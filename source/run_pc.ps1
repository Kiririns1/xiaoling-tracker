param([string]$DeviceHost='172.20.10.2',[ValidateSet(0,90,180,270)][int]$Rotate=90,[string]$PythonPath='',[switch]$CheckOnly)
$ErrorActionPreference='Stop'
$env:PYTHONUNBUFFERED='1'
$env:PYTHONIOENCODING='utf-8'
$python=$null
$candidates=New-Object System.Collections.Generic.List[string]
if($PythonPath){$candidates.Add($PythonPath)}
else{
 $candidates.Add((Join-Path $PSScriptRoot '.venv/Scripts/python.exe'))
 # Extracted deliverables can reuse setup from the containing source project.
 $ancestor=Split-Path -Parent $PSScriptRoot
 for($i=0;$i -lt 3 -and $ancestor;$i++){
  if(Test-Path -LiteralPath (Join-Path $ancestor 'pc/tracker_camera.py')){
   $candidates.Add((Join-Path $ancestor '.venv/Scripts/python.exe'))
  }
  $ancestor=Split-Path -Parent $ancestor
 }
 $candidates.Add((Join-Path $PSScriptRoot '../esp_opencv/.venv-xiaoling/Scripts/python.exe'))
}
foreach($candidate in ($candidates | Select-Object -Unique)){
 if(!(Test-Path -LiteralPath $candidate -PathType Leaf)){continue}
 try{
  $probe=& $candidate -c "import cv2,numpy,mediapipe; print('XIAOLING_RUNTIME_OK')" 2>$null
  if($LASTEXITCODE -eq 0 -and $probe -contains 'XIAOLING_RUNTIME_OK'){$python=(Resolve-Path -LiteralPath $candidate).Path;break}
 }catch{}
}
if(!$python){
 $setup=Join-Path $PSScriptRoot 'setup_pc.ps1'
 throw ('No working Python environment found for this copy. Run: powershell -ExecutionPolicy Bypass -File "{0}"' -f $setup)
}
Write-Host "Python environment: $python"
if($CheckOnly){Write-Host 'Python, OpenCV, NumPy and MediaPipe: OK';exit 0}
$env:MPLCONFIGDIR=Join-Path $PSScriptRoot 'pc/.mpl-cache'
$instance=[System.Threading.Mutex]::new($false,'Local\XiaolingGestureIMU')
if(!$instance.WaitOne(0)){Write-Host 'Gesture window is already running.';$instance.Dispose();exit 0}
try{& $python (Join-Path $PSScriptRoot 'pc/tracker_camera.py') --host $DeviceHost --rotate $Rotate}
finally{$instance.ReleaseMutex();$instance.Dispose()}
