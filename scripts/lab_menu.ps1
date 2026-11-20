#requires -Version 5.1
<#
SentinelIoT - menu operacional do laboratorio de rede domestica simulada.

Topologia:
  sentinel-router (OpenWrt)  NIC1 LAB-WAN, NIC2 LAB-LAN, NIC3 host-only (#2)
  sentinel-mint   (Mint)     NIC1 LAB-LAN, NIC2 host-only (#2)
  kali            (atacante) NIC1 LAB-LAN, NIC2 LAB-WAN

Regras de seguranca:
  - Nenhuma VM pode usar bridge, NAT ou NAT network.
  - As unicas redes internas permitidas sao LAB-LAN e LAB-WAN.
  - O unico adaptador host-only permitido e o #2 (192.168.57.0/24).
  - O menu nunca altera a rede fisica do host.

Uso:
  powershell -ExecutionPolicy Bypass -File scripts\lab_menu.ps1
  powershell -ExecutionPolicy Bypass -File scripts\lab_menu.ps1 -Action status
#>

[CmdletBinding()]
param(
    [ValidateSet('menu', 'status', 'isolation', 'start', 'stop', 'snapshots',
        'snapshot-take', 'snapshot-restore', 'kali-lan-only', 'kali-dual-homed',
        'internet-on', 'internet-off')]
    [string]$Action = 'menu',

    [string]$Vm,
    [string]$SnapshotName,
    [switch]$WithKali,
    [switch]$SkipIsolationCheck
)

$ErrorActionPreference = 'Continue'

$script:VBoxManage = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path $script:VBoxManage)) {
    $found = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($null -eq $found) {
        throw 'VBoxManage não encontrado. Ajuste o caminho no topo de scripts\lab_menu.ps1.'
    }
    $script:VBoxManage = $found.Source
}

$script:Router = 'sentinel-router'
$script:Kali = 'kali-linux-2025.4-virtualbox-amd64'
$script:Mint = 'sentinel-mint'
$script:MgmtHostOnly = '192.168.57.2'
$script:AllowedIntnets = @('LAB-LAN', 'LAB-WAN')
$script:AllowedHostonly = 'VirtualBox Host-Only Ethernet Adapter #2'
$script:SerialPorts = @{ $script:Router = 9001; $script:Mint = 9002 }

$script:Vms = @(
    [pscustomobject]@{ Name = $script:Router; Role = 'Roteador/firewall OpenWrt'; Ram = 256 }
    [pscustomobject]@{ Name = $script:Mint; Role = 'Dispositivo IoT simulado (Mint)'; Ram = 1536 }
    [pscustomobject]@{ Name = $script:Kali; Role = 'Atacante (Kali)'; Ram = 1536 }
)

function Invoke-VBox {
    param([string[]]$VBoxArgs)

    $output = & $script:VBoxManage @VBoxArgs 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = @($output | ForEach-Object { "$_" })
    }
}

function Get-VmInfo {
    param([string]$Name)

    $result = Invoke-VBox @('showvminfo', $Name, '--machinereadable')
    $map = @{}
    foreach ($line in $result.Output) {
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $Matches[1]
            $value = $Matches[2].Trim('"')
            $map[$key] = $value
        }
    }

    return [pscustomobject]@{
        Name    = $Name
        State   = if ($map.ContainsKey('VMState')) { $map['VMState'] } else { 'unknown' }
        Map     = $map
        ExitCode = $result.ExitCode
    }
}

function Get-VmState {
    param([string]$Name)
    return (Get-VmInfo -Name $Name).State
}

function Get-FreeMemoryMb {
    try {
        $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        return [math]::Round($os.FreePhysicalMemory / 1KB, 0)
    }
    catch {
        return $null
    }
}

function Wait-TcpPort {
    param(
        [string]$ComputerName,
        [int]$Port,
        [int]$TimeoutSec = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $client.BeginConnect($ComputerName, $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000) -and $client.Connected) {
                $client.Close()
                return $true
            }
        }
        catch {
        }
        finally {
            $client.Close()
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-LabVm {
    param([string]$Name)

    $state = Get-VmState -Name $Name
    if ($state -eq 'running') {
        Write-Host "[OK]    $Name já está em execução." -ForegroundColor Green
        return $true
    }
    if ($state -notin @('poweroff', 'aborted', 'saved')) {
        Write-Host "[ERRO]  $Name está no estado '$state'; não é possível iniciar." -ForegroundColor Red
        return $false
    }

    $result = Invoke-VBox @('startvm', $Name, '--type', 'headless')
    if ($result.ExitCode -ne 0) {
        Write-Host "[ERRO]  Falha ao iniciar $Name" -ForegroundColor Red
        $result.Output | ForEach-Object { Write-Host "        $_" }
        return $false
    }

    Write-Host "[OK]    $Name iniciado (headless)." -ForegroundColor Green
    return $true
}

function Stop-LabVm {
    param(
        [string]$Name,
        [int]$TimeoutSec = 45
    )

    $state = Get-VmState -Name $Name
    if ($state -eq 'poweroff') {
        Write-Host "[OK]    $Name já está desligado." -ForegroundColor Green
        return $true
    }

    Write-Host "[..]    Desligando $Name (ACPI)..." -NoNewline
    $null = Invoke-VBox @('controlvm', $Name, 'acpipowerbutton')

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-VmState -Name $Name) -eq 'poweroff') {
            Write-Host " desligado." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 1
    }

    Write-Host " timeout; forçando poweroff." -ForegroundColor Yellow
    $null = Invoke-VBox @('controlvm', $Name, 'poweroff')
    Start-Sleep -Seconds 2
    return ((Get-VmState -Name $Name) -eq 'poweroff')
}

function Show-Status {
    Write-Host ''
    Write-Host '=== Estado do laboratorio SentinelIoT ===' -ForegroundColor Cyan

    $freeMb = Get-FreeMemoryMb
    if ($null -ne $freeMb) {
        $color = if ($freeMb -lt 3500) { 'Yellow' } else { 'Green' }
        Write-Host ("Memoria livre no host: {0} MB" -f $freeMb) -ForegroundColor $color
    }

    foreach ($vm in $script:Vms) {
        $info = Get-VmInfo -Name $vm.Name
        if ($info.ExitCode -ne 0) {
            Write-Host ("[FALTA] {0} ({1})" -f $vm.Name, $vm.Role) -ForegroundColor Red
            continue
        }

        $stateColor = switch ($info.State) {
            'running' { 'Green' }
            'poweroff' { 'DarkGray' }
            default { 'Yellow' }
        }
        Write-Host ("{0,-45} {1,-10} {2}" -f $vm.Name, $info.State, $vm.Role) -ForegroundColor $stateColor

        foreach ($key in ($info.Map.Keys | Sort-Object)) {
            if ($key -notmatch '^nic(\d+)$') { continue }
            $index = $Matches[1]
            $type = $info.Map[$key]
            if ($type -eq 'none') { continue }

            $detail = switch ($type) {
                'intnet' { "intnet=$($info.Map["intnet$index"])" }
                'hostonly' { "hostonly=$($info.Map["hostonlyadapter$index"])" }
                'bridged' { "BRIDGE=$($info.Map["bridgeadapter$index"])" }
                'nat' { 'NAT' }
                'natnetwork' { "NATNETWORK=$($info.Map["natnet$index"])" }
                default { $type }
            }
            $cable = $info.Map["cableconnected$index"]
            Write-Host ("    NIC{0}: {1} (cabo={2})" -f $index, $detail, $cable)
        }

        if ($script:SerialPorts.ContainsKey($vm.Name)) {
            $serial = $info.Map['uartmode1']
            if ($serial) {
                Write-Host ("    serial: {0} -> localhost:{1}" -f $serial, $script:SerialPorts[$vm.Name])
            }
        }
    }

    Write-Host ''
    $routerInfo = Get-VmInfo -Name $script:Router
    if ($routerInfo.ExitCode -eq 0 -and $routerInfo.Map['nic4'] -eq 'nat') {
        if ($routerInfo.Map['cableconnected4'] -eq 'on') {
            Write-Host 'Internet de provisionamento: ATIVA (NIC4 NAT; isolamento reduzido)' -ForegroundColor Yellow
        }
        else {
            Write-Host 'Internet de provisionamento: desligada (NIC4 NAT, cabo off)' -ForegroundColor DarkGray
        }
    }
    Write-Host 'Redes internas: LAB-LAN = 10.10.10.0/24 | LAB-WAN = 203.0.113.0/24'
    Write-Host 'Gerencia host-only: 192.168.57.0/24 (roteador em 192.168.57.2)'
    Write-Host ''
}

function Test-Isolation {
    param([switch]$SkipNetworkCheck)

    Write-Host ''
    Write-Host '=== Teste de isolamento ===' -ForegroundColor Cyan

    $issues = New-Object System.Collections.Generic.List[string]
    $warnings = New-Object System.Collections.Generic.List[string]

    foreach ($vm in $script:Vms) {
        $info = Get-VmInfo -Name $vm.Name
        if ($info.ExitCode -ne 0) {
            $issues.Add("VM ausente: $($vm.Name)")
            continue
        }

        $activeNics = 0
        foreach ($key in $info.Map.Keys) {
            if ($key -notmatch '^nic(\d+)$') { continue }
            $index = $Matches[1]
            $type = $info.Map[$key]
            if ($type -eq 'none') { continue }
            $activeNics++

            switch ($type) {
                'intnet' {
                    $network = $info.Map["intnet$index"]
                    if ($network -notin $script:AllowedIntnets) {
                        $issues.Add("$($vm.Name) NIC$index usa rede interna nao permitida '$network'")
                    }
                    if ($info.Map["cableconnected$index"] -ne 'on') {
                        $warnings.Add("$($vm.Name) NIC$index ($network) esta com o cabo desconectado")
                    }
                }
                'hostonly' {
                    $adapter = $info.Map["hostonlyadapter$index"]
                    if ($adapter -ne $script:AllowedHostonly) {
                        $issues.Add("$($vm.Name) NIC$index usa host-only nao permitido '$adapter'")
                    }
                }
                'bridged' {
                    $issues.Add("$($vm.Name) NIC$index esta em BRIDGE ($($info.Map["bridgeadapter$index"]))")
                }
                'nat' {
                    if ($vm.Name -eq $script:Router -and $index -eq '4') {
                        if ($info.Map["cableconnected$index"] -eq 'on') {
                            $issues.Add("$($vm.Name) NIC4 em NAT: Internet de provisionamento ATIVA")
                        }
                        else {
                            $warnings.Add("$($vm.Name) NIC4 NAT presente, mas cabo desconectado")
                        }
                    }
                    else {
                        $issues.Add("$($vm.Name) NIC$index esta em NAT")
                    }
                }
                'natnetwork' {
                    $issues.Add("$($vm.Name) NIC$index esta em NAT network ($($info.Map["natnet$index"]))")
                }
                default {
                    $issues.Add("$($vm.Name) NIC$index usa modo nao permitido '$type'")
                }
            }
        }

        if ($activeNics -eq 0) {
            $issues.Add("$($vm.Name) nao tem nenhuma NIC ativa")
        }
    }

    $router = Get-VmInfo -Name $script:Router
    if ($router.ExitCode -eq 0) {
        $routerNets = @()
        foreach ($key in $router.Map.Keys) {
            if ($key -match '^intnet(\d+)$') { $routerNets += $router.Map[$key] }
        }
        if ('LAB-LAN' -notin $routerNets) { $issues.Add('O roteador nao esta conectado em LAB-LAN') }
        if ('LAB-WAN' -notin $routerNets) { $issues.Add('O roteador nao esta conectado em LAB-WAN') }
    }

    $mint = Get-VmInfo -Name $script:Mint
    if ($mint.ExitCode -eq 0) {
        $mintNets = @()
        foreach ($key in $mint.Map.Keys) {
            if ($key -match '^intnet(\d+)$') { $mintNets += $mint.Map[$key] }
        }
        if ('LAB-LAN' -notin $mintNets) { $issues.Add('O sentinel-mint nao esta conectado em LAB-LAN') }
    }

    $kali = Get-VmInfo -Name $script:Kali
    if ($kali.ExitCode -eq 0) {
        if ($kali.Map['cableconnected2'] -eq 'on') {
            $warnings.Add('Kali esta dual-homed (NIC2 LAB-WAN com cabo conectado)')
        }
    }

    if (-not $SkipNetworkCheck) {
        if (Wait-TcpPort -ComputerName $script:MgmtHostOnly -Port 80 -TimeoutSec 3) {
            Write-Host "[OK]    Gerencia do roteador responde em http://$($script:MgmtHostOnly)/" -ForegroundColor Green
        }
        else {
            Write-Host "[..]    Gerencia do roteador indisponivel (VM desligada ou ainda iniciando)" -ForegroundColor Yellow
        }
    }

    Write-Host ''
    if ($issues.Count -eq 0) {
        Write-Host 'RESULTADO: isolamento OK. Nenhum bridge, NAT ou rede externa detectado.' -ForegroundColor Green
    }
    else {
        Write-Host 'RESULTADO: FALHA no isolamento.' -ForegroundColor Red
        foreach ($issue in $issues) { Write-Host "  - $issue" -ForegroundColor Red }
    }
    foreach ($warning in $warnings) { Write-Host "  [aviso] $warning" -ForegroundColor Yellow }

    Write-Host ''
    Write-Host 'Verificacao complementar dentro das VMs:'
    Write-Host '  ip route'
    Write-Host '  getent hosts example.com || true'
    Write-Host '  curl --max-time 3 http://example.com || true'
    Write-Host '  ping -c 2 192.0.2.1 || true'  # faixa de exemplo (RFC 5737)
    Write-Host ''

    return ($issues.Count -eq 0)
}

function Start-Lab {
    param([switch]$IncludeKali)

    if (-not $SkipIsolationCheck) {
        if (-not (Test-Isolation -SkipNetworkCheck)) {
            Write-Host 'Inicio abortado: corrija o isolamento antes de ligar o laboratorio.' -ForegroundColor Red
            return $false
        }
    }

    $freeMb = Get-FreeMemoryMb
    $neededMb = 256 + 1536
    if ($IncludeKali) { $neededMb += 1536 }
    if ($null -ne $freeMb -and $freeMb -lt ($neededMb + 512)) {
        Write-Host ("[aviso] Memoria livre: {0} MB; o laboratorio pode precisar de ~{1} MB." -f $freeMb, $neededMb) -ForegroundColor Yellow
    }

    Write-Host ''
    if (-not (Start-LabVm -Name $script:Router)) { return $false }

    Write-Host '[..]    Aguardando a gerencia do roteador em 192.168.57.2:80...' -NoNewline
    if (Wait-TcpPort -ComputerName $script:MgmtHostOnly -Port 80 -TimeoutSec 90) {
        Write-Host ' pronto.' -ForegroundColor Green
    }
    else {
        Write-Host ' sem resposta; siga com o console serial 9001.' -ForegroundColor Yellow
    }

    if (-not (Start-LabVm -Name $script:Mint)) { return $false }

    if ($IncludeKali) {
        if (-not (Start-LabVm -Name $script:Kali)) { return $false }
    }

    Write-Host ''
    Write-Host 'Laboratorio iniciado. Consoles seriais: roteador 9001, Mint 9002.' -ForegroundColor Green
    return $true
}

function Stop-Lab {
    Write-Host ''
    foreach ($vm in @($script:Kali, $script:Mint, $script:Router)) {
        $null = Stop-LabVm -Name $vm
    }
}

function Set-LabInternet {
    param([bool]$Enabled)

    $state = Get-VmState -Name $script:Router
    $info = Get-VmInfo -Name $script:Router
    $nic4 = $info.Map['nic4']
    $cable = if ($Enabled) { 'on' } else { 'off' }

    if ($state -eq 'running') {
        if ($nic4 -eq 'none') {
            Write-Host '[ERRO]  NIC4 ainda nao existe. Desligue o roteador uma vez e rode este item de novo.' -ForegroundColor Red
            return $false
        }
        $result = Invoke-VBox @('controlvm', $script:Router, 'setlinkstate4', $cable)
    }
    else {
        $result = Invoke-VBox @('modifyvm', $script:Router, '--nic4', 'nat',
            '--nictype4', 'virtio', '--cableconnected4', $cable)
    }

    if ($result.ExitCode -ne 0) {
        Write-Host '[ERRO]  Falha ao ajustar a Internet do laboratorio.' -ForegroundColor Red
        $result.Output | ForEach-Object { Write-Host "        $_" }
        return $false
    }

    if ($Enabled) {
        Write-Host '[OK]    NIC4 (NAT) conectada. Se o roteador ja estava ligado, rode no console 9001:' -ForegroundColor Green
        Write-Host '        ifup wan_inet'
    }
    else {
        Write-Host '[OK]    NIC4 (NAT) desconectada. Laboratorio voltou ao isolamento.' -ForegroundColor Green
    }
    return $true
}

function Set-KaliMode {
    param([ValidateSet('lan-only', 'dual-homed')][string]$Mode)

    $kaliState = Get-VmState -Name $script:Kali
    $cable = if ($Mode -eq 'dual-homed') { 'on' } else { 'off' }

    if ($kaliState -eq 'running') {
        $result = Invoke-VBox @('controlvm', $script:Kali, 'setlinkstate2', $cable)
    }
    else {
        $result = Invoke-VBox @('modifyvm', $script:Kali, '--cableconnected2', $cable)
    }

    if ($result.ExitCode -ne 0) {
        Write-Host "[ERRO]  Falha ao ajustar o modo do Kali." -ForegroundColor Red
        $result.Output | ForEach-Object { Write-Host "        $_" }
        return $false
    }

    if ($Mode -eq 'dual-homed') {
        Write-Host '[OK]    Kali dual-homed: NIC2 LAB-WAN conectada (rede ainda isolada).' -ForegroundColor Green
    }
    else {
        Write-Host '[OK]    Kali LAN-only: NIC2 LAB-WAN desconectada.' -ForegroundColor Green
    }
    return $true
}

function Show-Snapshots {
    Write-Host ''
    foreach ($vm in $script:Vms) {
        Write-Host "--- $($vm.Name)" -ForegroundColor Cyan
        $result = Invoke-VBox @('snapshot', $vm.Name, 'list')
        if ($result.ExitCode -ne 0 -or $result.Output.Count -eq 0) {
            Write-Host '    (sem snapshots)'
            continue
        }
        $count = 0
        foreach ($line in $result.Output) {
            if ($line.Trim() -eq '' -or $line -match 'contains no snapshots') { continue }
            $count++
            Write-Host "    $line"
        }
        if ($count -eq 0) { Write-Host '    (sem snapshots)' }
    }
    Write-Host ''
}

function New-LabSnapshot {
    param(
        [string]$Name,
        [string]$TargetVm
    )

    if (-not $Name) {
        $Name = Read-Host 'Nome do snapshot'
    }
    if (-not $Name) {
        Write-Host '[ERRO]  Nome do snapshot vazio.' -ForegroundColor Red
        return $false
    }

    $targets = if ($TargetVm) { @($TargetVm) } else { @($script:Router, $script:Mint) }
    foreach ($vm in $targets) {
        if ($vm -eq $script:Kali) {
            Write-Host '[ERRO]  O Kali nao recebe snapshot automaticamente.' -ForegroundColor Red
            return $false
        }
        Write-Host "[..]    Criando snapshot '$Name' em $vm"
        $result = Invoke-VBox @('snapshot', $vm, 'take', $Name)
        if ($result.ExitCode -ne 0) {
            Write-Host "[ERRO]  Falha em $vm" -ForegroundColor Red
            $result.Output | ForEach-Object { Write-Host "        $_" }
            return $false
        }
        Write-Host "[OK]    Snapshot criado em $vm" -ForegroundColor Green
    }
    return $true
}

function Restore-LabSnapshot {
    param(
        [string]$Name,
        [string]$TargetVm
    )

    if (-not $Name) {
        $Name = Read-Host 'Nome do snapshot a restaurar'
    }
    if (-not $Name) {
        Write-Host '[ERRO]  Nome do snapshot vazio.' -ForegroundColor Red
        return $false
    }

    $targets = if ($TargetVm) { @($TargetVm) } else { @($script:Router, $script:Mint) }
    foreach ($vm in $targets) {
        $state = Get-VmState -Name $vm
        if ($state -ne 'poweroff') {
            Write-Host "[ERRO]  $vm precisa estar desligado para restaurar (estado: $state)." -ForegroundColor Red
            return $false
        }
        if (-not $Force) {
            $answer = Read-Host "Restaurar snapshot '$Name' em $vm e descartar o estado atual? [s/N]"
            if ($answer -notmatch '^(s|sim|y|yes)$') {
                Write-Host 'Cancelado.'
                return $false
            }
        }
        Write-Host "[..]    Restaurando '$Name' em $vm"
        $result = Invoke-VBox @('snapshot', $vm, 'restore', $Name)
        if ($result.ExitCode -ne 0) {
            Write-Host "[ERRO]  Falha em $vm" -ForegroundColor Red
            $result.Output | ForEach-Object { Write-Host "        $_" }
            return $false
        }
        Write-Host "[OK]    Snapshot restaurado em $vm" -ForegroundColor Green
    }
    return $true
}

function Connect-SerialConsole {
    param([int]$Port)

    Write-Host "Conectando em localhost:$Port (Ctrl+] para sair)..." -ForegroundColor Cyan
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Port)
    }
    catch {
        Write-Host "[ERRO]  Nao foi possivel conectar: $($_.Exception.Message)" -ForegroundColor Red
        $client.Close()
        return
    }

    $stream = $client.GetStream()
    $stream.ReadTimeout = 200
    $buffer = New-Object byte[] 4096
    $quit = $false

    try {
        while (-not $quit) {
            try {
                while ($stream.DataAvailable) {
                    $read = $stream.Read($buffer, 0, $buffer.Length)
                    if ($read -le 0) { break }
                    Write-Host -NoNewline ([System.Text.Encoding]::UTF8.GetString($buffer, 0, $read))
                }
            }
            catch [System.IO.IOException] {
            }

            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq [ConsoleKey]::Escape) { break }
                if ($key.Key -eq [ConsoleKey]::Enter) { $stream.Write([byte[]](13), 0, 1) }
                elseif ($key.Key -eq [ConsoleKey]::Backspace) { $stream.Write([byte[]](127), 0, 1) }
                elseif ($key.KeyChar -eq ']' -and ($key.Modifiers -band [ConsoleModifiers]::Control)) { break }
                elseif ($key.KeyChar) {
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$key.KeyChar)
                    $stream.Write($bytes, 0, $bytes.Length)
                }
                $stream.Flush()
            }
            Start-Sleep -Milliseconds 30
        }
    }
    finally {
        $stream.Close()
        $client.Close()
        Write-Host ''
        Write-Host 'Console encerrado.'
    }
}

function Show-Menu {
    Write-Host ''
    Write-Host '==============================================' -ForegroundColor Cyan
    Write-Host '  ____             _   _            _ 
/ ___|  ___ _ __ | |_(_)_ __   ___| |
\___ \ / _ | '_ \| __| | '_ \ / _ | |
 ___) |  __| | | | |_| | | | |  __| |
|____/ \___|_| |_|\__|_|_| |_|\___|_| Laboratorio de rede simulada' -ForegroundColor Cyan
    Write-Host '==============================================' -ForegroundColor Cyan
    Write-Host ' 1) Status das VMs e redes'
    Write-Host ' 2) Teste de isolamento'
    Write-Host ' 3) Iniciar laboratorio (roteador + Mint)'
    Write-Host ' 4) Iniciar laboratorio + Kali'
    Write-Host ' 5) Parar laboratorio'
    Write-Host ' 6) Console serial do roteador (9001)'
    Write-Host ' 7) Console serial do Mint (9002)'
    Write-Host ' 8) Kali LAN-only (NIC2 desconectada)'
    Write-Host ' 9) Kali dual-homed (NIC2 LAB-WAN)'
    Write-Host ' 10) Internet ON  (NAT no roteador - provisionamento)'
    Write-Host ' 11) Internet OFF (volta ao isolamento)'
    Write-Host ' S) Listar snapshots'
    Write-Host ' T) Criar snapshot (roteador + Mint)'
    Write-Host ' R) Restaurar snapshot (roteador + Mint)'
    Write-Host ' 0) Sair'
    Write-Host ''
}

function Invoke-Menu {
    $running = $true
    while ($running) {
        Show-Menu
        $choice = Read-Host 'Opcao'
        switch ($choice) {
            '1' { Show-Status }
            '2' { $null = Test-Isolation }
            '3' { $null = Start-Lab }
            '4' { $null = Start-Lab -IncludeKali }
            '5' { Stop-Lab }
            '6' { Connect-SerialConsole -Port $script:SerialPorts[$script:Router] }
            '7' { Connect-SerialConsole -Port $script:SerialPorts[$script:Mint] }
            '8' { $null = Set-KaliMode -Mode 'lan-only' }
            '9' { $null = Set-KaliMode -Mode 'dual-homed' }
            '10' { $null = Set-LabInternet -Enabled $true }
            '11' { $null = Set-LabInternet -Enabled $false }
            'S' { Show-Snapshots }
            'T' { $null = New-LabSnapshot }
            'R' { $null = Restore-LabSnapshot }
            '0' { $running = $false }
            default { Write-Host 'Opcao invalida.' -ForegroundColor Yellow }
        }
    }
}

switch ($Action) {
    'status' { Show-Status }
    'isolation' { $null = Test-Isolation }
    'start' { $null = Start-Lab -IncludeKali:$WithKali }
    'stop' { Stop-Lab }
    'snapshots' { Show-Snapshots }
    'snapshot-take' { $null = New-LabSnapshot -Name $SnapshotName -TargetVm $Vm }
    'snapshot-restore' { $null = Restore-LabSnapshot -Name $SnapshotName -TargetVm $Vm }
    'kali-lan-only' { $null = Set-KaliMode -Mode 'lan-only' }
    'kali-dual-homed' { $null = Set-KaliMode -Mode 'dual-homed' }
    'internet-on' { $null = Set-LabInternet -Enabled $true }
    'internet-off' { $null = Set-LabInternet -Enabled $false }
    'menu' { Invoke-Menu }
}
