# Reverse-TCP-DLL
When you need a simple TCP reverse shell.

# build_payload
This tool contains an already compiled DLL, but the DLL lacks a destination IPv4 address and port.
You can provide the destination, port, and export name from the command line:
![image](https://user-images.githubusercontent.com/21281361/221787857-53649369-89a8-4122-b641-8d860bacde18.png)

## Sections:
The way this works is it searches through the DLL for offsets.
The IP address and port are a global structure, so they located in a specific place in the PE file:

![image](https://user-images.githubusercontent.com/21281361/221783915-00d86dd1-bf51-49b2-9dea-22532c876029.png)

The same is true of the export name. This is limited to 15 characters:

![image](https://user-images.githubusercontent.com/21281361/221783767-7ffedadc-95bf-4c24-9e72-832e726e1afc.png)

These sections are searched for as "needles", and then replaced with the provided address and port.
This allows the created file to be caught with a simple NC or SOCAT listener.
![image](https://user-images.githubusercontent.com/21281361/221787506-d1a04279-9cad-45be-aace-db9aad64998b.png)
