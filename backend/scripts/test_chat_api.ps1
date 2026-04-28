$BaseUrl = "http://127.0.0.1:8000"
$Email = "test@example.com"
$Password = "12345678"

$loginBody = @{
    email = $Email
    password = $Password
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Uri "$BaseUrl/auth/login" `
    -Method Post `
    -Body $loginBody `
    -ContentType "application/json"

$headers = @{
    Authorization = "Bearer $($login.access_token)"
}

$demoBody = @{
    message = "Tell me about timetable API"
} | ConvertTo-Json

Write-Host "== Demo Chat =="
Invoke-RestMethod `
    -Uri "$BaseUrl/api/chat/demo" `
    -Method Post `
    -Body $demoBody `
    -ContentType "application/json" | ConvertTo-Json -Depth 5

$roomBody = @{
    title = "API test chat room"
} | ConvertTo-Json

Write-Host "== Create Room =="
$room = Invoke-RestMethod `
    -Uri "$BaseUrl/api/chat/rooms" `
    -Method Post `
    -Body $roomBody `
    -ContentType "application/json" `
    -Headers $headers
$room | ConvertTo-Json -Depth 5

$messageBody = @{
    content = "How can I use notice and daily menu APIs?"
} | ConvertTo-Json

Write-Host "== Send Message =="
Invoke-RestMethod `
    -Uri "$BaseUrl/api/chat/rooms/$($room.id)/messages" `
    -Method Post `
    -Body $messageBody `
    -ContentType "application/json" `
    -Headers $headers | ConvertTo-Json -Depth 5

Write-Host "== List Messages =="
Invoke-RestMethod `
    -Uri "$BaseUrl/api/chat/rooms/$($room.id)/messages" `
    -Method Get `
    -Headers $headers | ConvertTo-Json -Depth 5
