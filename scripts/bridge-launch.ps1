param(
    [switch]$CheckOnly,
    [switch]$ForcePassword
)

$argsList = @()
if ($CheckOnly) { $argsList += "--check-only" }
if ($ForcePassword) { $argsList += "--force-password" }

docker compose exec backend python scripts/bridge_launch.py @argsList
