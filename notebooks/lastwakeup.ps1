# Define the filter
$Filter = @{
    LogName = 'System'
    Id = 1
    ProviderName = 'Microsoft-Windows-Power-Troubleshooter'
}

# Get the events
$WakeupEvents = Get-WinEvent -FilterHashtable $Filter -MaxEvents 10

# Display the results
$WakeupEvents | ForEach-Object {
    $event = $_ | Select-Object -Property TimeCreated, Id, ProviderName, Message
    $msg = $event.Message -replace '\s+', ' '  # Remove extra spaces
    Write-Host "TimeCreated: $($event.TimeCreated)"
    Write-Host "Event ID: $($event.Id)"
    Write-Host "Provider Name: $($event.ProviderName)"
    Write-Host "Message: $msg"
    Write-Host ""
}
