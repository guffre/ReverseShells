FOR %%d IN (client server) DO (
    cd %~dp0/%%d
    FOR %%o IN (linux windows) DO (
        SET GOOS=%%o
        for %%a in (386 amd64) do (
            SET GOARCH=%%a
            if "%%o" == "linux" (
                go build -ldflags="-s -w" -v -o %%d-%%a-%%o
            ) ELSE (
                go build -ldflags="-s -w" -v -o %%d-%%a.exe
            )
        )
    )
)