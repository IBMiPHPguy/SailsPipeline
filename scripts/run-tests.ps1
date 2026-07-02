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
            -e DATABASE_URL=mysql+pymysql://root:testroot@test-db:3306/sailspipeline_test `
            backend-test `
            pytest tests/unit -v --cov=app.workflow_helpers --cov=app.proposed_cruise_helpers --cov=app.passenger_helpers --cov=app.research_proposal_email --cov=app.audit_helpers --cov=app.security --cov=app.services.gemini_context_service --cov=app.services.proposed_cruise_service --cov-config=.coveragerc --cov-report=term-missing:skip-covered --cov-fail-under=95
    }
    finally {
        Pop-Location
    }
}

function Run-BackendIntegrationTests {
    Push-Location $PSScriptRoot
    try {
        docker compose --profile test up -d test-db | Out-Null
        docker compose --profile test run --rm backend-test pytest tests/integration -v
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
