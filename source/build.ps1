param([ValidateSet('build','flash','flashfull')][string]$Action='build',[string]$Port='COM3',
 [string]$IdfPath='C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer/esp-idf',
 [string]$ToolsPath='C:/Users/kiririns/Documents/ChatGPT/hack/esp_idf_tools')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot.Replace('\','/')
$env:ADF_PATH=$root
$env:IDF_PATH=$IdfPath
$env:IDF_TOOLS_PATH=$ToolsPath
$env:IDF_PYTHON_ENV_PATH="$env:IDF_TOOLS_PATH/python_env/idf5.4_py3.12_env"
$env:IDF_COMPONENT_MANAGER='1'
$env:GIT_CONFIG_COUNT='1'
$env:GIT_CONFIG_KEY_0='safe.directory'
$env:GIT_CONFIG_VALUE_0='C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer'
$tc="$env:IDF_TOOLS_PATH/tools"
$env:PATH="$tc/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin;$tc/cmake/3.30.2/bin;$tc/ninja/1.12.1;$tc/esp32ulp-elf/2.38_20240113/esp32ulp-elf/bin;$env:PATH"
$env:ESP_ROM_ELF_DIR="$tc/esp-rom-elfs/20241011"
$py="$env:IDF_PYTHON_ENV_PATH/Scripts/python.exe"
if($Action -eq 'flash' -or $Action -eq 'flashfull') {
 Push-Location "$root/apps/build"
 try {
  $argFile=if($Action -eq 'flashfull'){'@flash_args'}else{'@app-flash_args'}
  if(!(Test-Path -LiteralPath $argFile.Substring(1))){throw 'Build the project before flashing.'}
  & $py -m esptool --chip esp32s3 --port $Port --baud 460800 --before default_reset --after hard_reset write_flash $argFile
 } finally {Pop-Location}
}
else {
 & "$tc/cmake/3.30.2/bin/cmake.exe" -S "$root/apps" -B "$root/apps/build" -G Ninja -DPYTHON_DEPS_CHECKED=1 "-DPYTHON=$py" -DESP_PLATFORM=1 -DCCACHE_ENABLE=0
 if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
 & "$tc/ninja/1.12.1/ninja.exe" -C "$root/apps/build"
}
exit $LASTEXITCODE
