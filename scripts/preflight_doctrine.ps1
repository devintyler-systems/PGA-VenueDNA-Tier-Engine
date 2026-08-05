[CmdletBinding()]
param(
    [string]$RepoRoot
)

Set-StrictMode -Version Latest

$exitCode = 0
$tempRoot = $null
$tempParent = $null
$environmentChanged = $false
$locationChanged = $false
$originalLocation = Get-Location

$hadDontWriteBytecode = Test-Path Env:PYTHONDONTWRITEBYTECODE
$previousDontWriteBytecode = if ($hadDontWriteBytecode) {
    (Get-Item Env:PYTHONDONTWRITEBYTECODE).Value
} else {
    $null
}

$hadPycachePrefix = Test-Path Env:PYTHONPYCACHEPREFIX
$previousPycachePrefix = if ($hadPycachePrefix) {
    (Get-Item Env:PYTHONPYCACHEPREFIX).Value
} else {
    $null
}

function Test-SafeCleanupTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate,

        [Parameter(Mandatory = $true)]
        [string]$ExpectedParent
    )

    try {
        $fullCandidate = [System.IO.Path]::GetFullPath($Candidate)
        $fullParent = [System.IO.Path]::GetFullPath($ExpectedParent).TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
        $candidateParent = [System.IO.Path]::GetDirectoryName($fullCandidate).TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
        $candidateName = [System.IO.Path]::GetFileName($fullCandidate)
    } catch {
        return $false
    }

    return (
        [string]::Equals(
            $candidateParent,
            $fullParent,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -and
        $candidateName -match '^venuedna_doctrine_preflight_[0-9a-f]{32}$'
    )
}

try {
    try {
        if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
            $repoCandidate = Join-Path $PSScriptRoot ".."
        } else {
            $repoCandidate = $RepoRoot
        }
        $resolvedRepoRoot = [System.IO.Path]::GetFullPath($repoCandidate)
    } catch {
        throw "Repository root is invalid: $RepoRoot"
    }

    if (-not (Test-Path -LiteralPath $resolvedRepoRoot -PathType Container)) {
        throw "Repository root does not exist: $resolvedRepoRoot"
    }

    $pythonCommand = Get-Command -Name python -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $pythonCommand -or [string]::IsNullOrWhiteSpace($pythonCommand.Source)) {
        throw "Python is unavailable through Get-Command: python"
    }
    $pythonExecutable = $pythonCommand.Source

    $validatorPath = Join-Path $resolvedRepoRoot "tools\validate_scoring_doctrine.py"
    if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
        throw "Required path is missing: $validatorPath"
    }

    $tempParent = [System.IO.Path]::GetFullPath(
        [System.IO.Path]::GetTempPath()
    ).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    if (-not (Test-Path -LiteralPath $tempParent -PathType Container)) {
        throw "Operating-system temporary directory does not exist: $tempParent"
    }

    $tempName = "venuedna_doctrine_preflight_{0}" -f (
        [System.Guid]::NewGuid().ToString("N")
    )
    $tempRoot = Join-Path $tempParent $tempName
    if (-not (Test-SafeCleanupTarget -Candidate $tempRoot -ExpectedParent $tempParent)) {
        throw "Unsafe temporary-directory target"
    }
    if (Test-Path -LiteralPath $tempRoot) {
        throw "Unique temporary-directory target already exists"
    }
    New-Item -ItemType Directory -Path $tempRoot -ErrorAction Stop | Out-Null

    $environmentChanged = $true
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $env:PYTHONPYCACHEPREFIX = Join-Path $tempRoot "pycache"

    Set-Location -LiteralPath $resolvedRepoRoot -ErrorAction Stop
    $locationChanged = $true

    $steps = @(
        [PSCustomObject]@{
            Index = 1
            Label = "Strict doctrine validator"
            RequiredPath = "tools\validate_scoring_doctrine.py"
            Arguments = @(
                "tools\validate_scoring_doctrine.py",
                "--repo-root", $resolvedRepoRoot,
                "--strict"
            )
        },
        [PSCustomObject]@{
            Index = 2
            Label = "Doctrine contract tests"
            RequiredPath = "tests\test_doctrine_contract.py"
            Arguments = @(
                "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--basetemp", (Join-Path $tempRoot "pytest_doctrine"),
                "tests\test_doctrine_contract.py"
            )
        },
        [PSCustomObject]@{
            Index = 3
            Label = "Scoring decomposition tests"
            RequiredPath = "tests\test_scoring_decomposition.py"
            Arguments = @(
                "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--basetemp", (Join-Path $tempRoot "pytest_decomposition"),
                "tests\test_scoring_decomposition.py"
            )
        },
        [PSCustomObject]@{
            Index = 4
            Label = "Enrichment tests"
            RequiredPath = "tests\test_enrich_cards.py"
            Arguments = @(
                "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--basetemp", (Join-Path $tempRoot "pytest_enrich"),
                "tests\test_enrich_cards.py"
            )
        }
    )

    foreach ($step in $steps) {
        $requiredPath = Join-Path $resolvedRepoRoot $step.RequiredPath
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required path is missing: $requiredPath"
        }

        Write-Output ("[{0}/4] START {1}" -f $step.Index, $step.Label)
        $childArguments = $step.Arguments
        try {
            & $pythonExecutable @childArguments
            $childExitCode = $LASTEXITCODE
        } catch {
            Write-Output ("[{0}/4] FAIL  {1} (exit code 2)" -f $step.Index, $step.Label)
            throw "Unable to execute $($step.Label): $($_.Exception.Message)"
        }

        if ($childExitCode -ne 0) {
            Write-Output (
                "[{0}/4] FAIL  {1} (exit code {2})" -f
                $step.Index, $step.Label, $childExitCode
            )
            $exitCode = $childExitCode
            break
        }

        Write-Output ("[{0}/4] PASS  {1}" -f $step.Index, $step.Label)
        Write-Output ""
    }
} catch {
    $exitCode = 2
    [Console]::Error.WriteLine("DOCTRINE PREFLIGHT ERROR: {0}", $_.Exception.Message)
} finally {
    if ($locationChanged) {
        try {
            Set-Location -LiteralPath $originalLocation.Path -ErrorAction Stop
        } catch {
            $exitCode = 2
            [Console]::Error.WriteLine(
                "DOCTRINE PREFLIGHT ERROR: Could not restore the caller's working directory: {0}",
                $_.Exception.Message
            )
        }
    }

    if ($environmentChanged) {
        try {
            if ($hadDontWriteBytecode) {
                $env:PYTHONDONTWRITEBYTECODE = $previousDontWriteBytecode
            } else {
                Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction Stop
            }

            if ($hadPycachePrefix) {
                $env:PYTHONPYCACHEPREFIX = $previousPycachePrefix
            } else {
                Remove-Item Env:PYTHONPYCACHEPREFIX -ErrorAction Stop
            }
        } catch {
            $exitCode = 2
            [Console]::Error.WriteLine(
                "DOCTRINE PREFLIGHT ERROR: Could not restore Python environment variables: {0}",
                $_.Exception.Message
            )
        }
    }

    if ($null -ne $tempRoot) {
        if (-not (Test-SafeCleanupTarget -Candidate $tempRoot -ExpectedParent $tempParent)) {
            $exitCode = 2
            [Console]::Error.WriteLine(
                "DOCTRINE PREFLIGHT ERROR: Unsafe cleanup target; temporary content was not removed"
            )
        } elseif (Test-Path -LiteralPath $tempRoot) {
            try {
                Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction Stop
            } catch {
                $exitCode = 2
                [Console]::Error.WriteLine(
                    "DOCTRINE PREFLIGHT ERROR: Could not remove the temporary directory: {0}",
                    $_.Exception.Message
                )
            }
        }
    }
}

if ($exitCode -eq 0) {
    Write-Output "DOCTRINE PREFLIGHT PASSED"
} else {
    Write-Output "DOCTRINE PREFLIGHT FAILED"
}

exit $exitCode
