// x86_64-w64-mingw32-gcc socat.c
#include <stdio.h>
#include <process.h>
#include <windows.h>
#include "cygcrypto_1_1.h"
#include "cygncursesw_10.h"
#include "cygreadline7.h"
#include "cygssl_1_1.h"
#include "cygwin1.h"
#include "cygwrap_0.h"
#include "cygz.h"
#include "socat.h"

char* dropped_files[8];

char* drop_file(char* filename, unsigned char* bytes, unsigned int length) {
    HANDLE hTempFile = INVALID_HANDLE_VALUE; 
    BOOL fSuccess  = FALSE;
    DWORD dwRetVal = 0;
    UINT uRetVal   = 0;
    DWORD dwBytesWritten = 0; 
    TCHAR szTempFileName[MAX_PATH];  
    TCHAR lpTempPathBuffer[MAX_PATH];
    
    dwRetVal = GetTempPath(MAX_PATH, lpTempPathBuffer); // buffer for path 
    if (dwRetVal > MAX_PATH || (dwRetVal == 0)) {
        printf("GetTempPath failed\n");
        return (NULL);
    }

    //printf("temp path buffer: %s\n", lpTempPathBuffer);

    snprintf(szTempFileName, MAX_PATH, "%s%s", lpTempPathBuffer, filename);
    //printf("filename: %s\n", szTempFileName);

    hTempFile = CreateFile((LPTSTR) szTempFileName, // file name 
                           GENERIC_WRITE,        // open for write 
                           0,                    // do not share 
                           NULL,                 // default security 
                           CREATE_NEW,           // create if does not exist
                           FILE_ATTRIBUTE_NORMAL,// normal file 
                           NULL);                // no template 
    if (hTempFile == INVALID_HANDLE_VALUE) { 
        if (GetLastError() == ERROR_FILE_EXISTS) {
            CloseHandle(hTempFile);
            return strdup(szTempFileName);
        }
        printf("Second CreateFile failed\n");
        return (NULL);
    }

    do {
        fSuccess = WriteFile(hTempFile,
                            bytes, 
                            length,
                            &dwBytesWritten, 
                            NULL);
        if (!fSuccess) {
            printf("WriteFile failed\n");
            return (NULL);
        }
    }
    while (dwBytesWritten != length);
    
    CloseHandle(hTempFile);
    return strdup(szTempFileName);
}

int main(int argc, char** argv) {
    dropped_files[0] = drop_file("socat.exe", socat_exe, socat_exe_len);
    dropped_files[1] = drop_file("cygcrypto-1.1.dll", cygcrypto_1_1_dll, cygcrypto_1_1_dll_len);
    dropped_files[2] = drop_file("cygncursesw-10.dll", cygncursesw_10_dll, cygncursesw_10_dll_len);
    dropped_files[3] = drop_file("cygreadline7.dll", cygreadline7_dll, cygreadline7_dll_len);
    dropped_files[4] = drop_file("cygssl-1.1.dll", cygssl_1_1_dll, cygssl_1_1_dll_len);
    dropped_files[5] = drop_file("cygwin1.dll", cygwin1_dll, cygwin1_dll_len);
    dropped_files[6] = drop_file("cygwrap-0.dll", cygwrap_0_dll, cygwrap_0_dll_len);
    dropped_files[7] = drop_file("cygz.dll", cygz_dll, cygz_dll_len);
    //printf("socat: %s\n", dropped_files[0]);
    
    char arg_buff[4096];
    int buff_used = snprintf(arg_buff, 4096, "%s", dropped_files[0]);
    
    for (int i = 1; i < argc; i++) {
        snprintf(arg_buff+buff_used, 4096-buff_used, " %s", argv[i]);
        buff_used += 1 + strlen(argv[i]);
    }
    system(arg_buff);
    //_execve(dropped_files[0], argv, NULL);
}