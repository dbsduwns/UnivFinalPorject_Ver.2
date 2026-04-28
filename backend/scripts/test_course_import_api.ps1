$BaseUrl = "http://127.0.0.1:8000"

$html = @'
<html>
<body>
<form name="frm1">
<input type="hidden" name="schl_year" value="2026">
<input type="hidden" name="schl_smst" value="1">
<table class="grid_list">
<tr id="row1">
  <td>EF14215</td>
  <td>00</td>
  <td align="left">Security Application</td>
  <td align="left">Professor A</td>
  <td>3</td>
  <td>3</td>
  <td align="left">(day)WED1ab2ab3ab</td>
  <td>Syllabus</td>
</tr>
<tr id="row2">
  <td>EF14216</td>
  <td>01</td>
  <td align="left">Capstone Design SW I</td>
  <td align="left">Professor B</td>
  <td>3</td>
  <td>4</td>
  <td align="left">(day)THU1ab2ab3ab4ab</td>
  <td>Syllabus</td>
</tr>
</table>
</form>
</body>
</html>
'@

$body = @{
    html = $html
    department = "Software"
    save = $true
} | ConvertTo-Json

Write-Host "== Import Courses From HTML =="
Invoke-RestMethod `
    -Uri "$BaseUrl/api/courses/import-html" `
    -Method Post `
    -Body $body `
    -ContentType "application/json" | ConvertTo-Json -Depth 10

Write-Host "== List Courses =="
Invoke-RestMethod `
    -Uri "$BaseUrl/api/courses/" `
    -Method Get | ConvertTo-Json -Depth 10
