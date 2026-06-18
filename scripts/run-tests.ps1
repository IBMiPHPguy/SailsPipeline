param(
    [ValidateSet("unit", "integration", "all", "frontend")]
    [string]$Suite = "all"
)

$ErrorActionPreference = "Stop"

function Run-BackendUnitTests {
    Push-Location $PSScriptRoot
    try {
        docker compose --profile test up -d test-db | Out-Null
        docker compose --profile test run --rm `
            -e DATABASE_URL=mysql+pymysql://root:testroot@test-db:3306/cruisetravelnow_test `
            backend-test `
            sh -c "pip install --no-cache-dir -r requirements-dev.txt && pytest tests/unit -v"
    }
    finally {
        Pop-Location
    }
}

function Run-BackendIntegrationTests {
    Push-Location $PSScriptRoot
    try {
        docker compose --profile test up -d test-db | Out-Null
        docker compose --profile test run --rm backend-test `
            sh -c "pip install --no-cache-dir -r requirements-dev.txt && pytest tests/integration -v"
    }
    finally {
        Pop-Location
    }
}

function Run-BackendAllTests {
    Push-Location $PSScriptRoot
    try {
        docker compose --profile test up -d test-db | Out-Null
        docker compose --profile test run --rm backend-test
    }
    finally {
        Pop-Location
    }
}

function Run-FrontendTests {
    Push-Location $PSScriptRoot
    try {
        docker compose --profile test run --rm frontend-test
    }
    finally {
        Pop-Location
    }
}

switch ($Suite) {
    "unit" { Run-BackendUnitTests }
    "integration" { Run-BackendIntegrationTests }
    "frontend" { Run-FrontendTests }
    default {
        Run-BackendAllTests
        Run-FrontendTests
    }
}
