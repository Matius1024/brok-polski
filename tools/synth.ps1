param([string]$List, [string]$Voice, [int]$Rate = 0)
# Each line of $List: <wav path><TAB><text>. Writes one WAV per line with the given SAPI voice.
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate = $Rate
foreach ($line in [System.IO.File]::ReadAllLines($List, [System.Text.Encoding]::UTF8)) {
    $parts = $line -split "`t", 2
    if ($parts.Count -lt 2) { continue }
    try {
        $s.SetOutputToWaveFile($parts[0])
        $s.Speak($parts[1])
    } catch {
        Write-Host "FAIL $($parts[0]): $_"
    }
}
$s.SetOutputToNull()
$s.Dispose()
