# Manual Switch 2 Captive-Portal Check

This procedure checks normal captive-portal opening and visual access to the diagnostic cards. It does not run any WebKit diagnostic.

## Prepare the host

Confirm that the lab server listens on `<LAB_IP>:80`, then check HTTP and DNS from the host:

```sh
dig @<LAB_IP> ctest.p01.ctest.srv.nintendo.net A
curl -i --resolve ctest.p01.ctest.srv.nintendo.net:80:<LAB_IP> \
  http://ctest.p01.ctest.srv.nintendo.net/
curl -I --resolve ctest.p01.ctest.srv.nintendo.net:80:<LAB_IP> \
  http://ctest.p01.ctest.srv.nintendo.net/
```

The A record should point to the lab address. GET `/` should serve the WebKit2JB HTML with HTTP 200; HEAD should return the same status and content length with no body. The root does not redirect: it is the portal destination.

The local `dnsmasq` profiles use port 53 and the lab address. They are alternatives and must not be run simultaneously. Do not stop or replace an active network service without identifying its owner and preparing a rollback.

## On the Switch 2

1. In the test Wi-Fi connection settings, set the Switch DNS to manual and enter `<LAB_IP>` as the primary DNS. Do not change the host or router DNS.
2. Start **Test Connection** from Network Settings. If the sign-in/portal prompt appears, open the portal from that prompt. Do not type a URL into the browser.
3. Confirm that the WebKit2JB page appears. From the home screen, open **API availability**, **Local font loading**, and **JavaScript reentrancy**. Confirm each shows its ready state and that no diagnostic has run. Do not press **Run**.
4. Exit the portal and restore that Wi-Fi connection's DNS setting to **Automatic**.

Record the exact result (portal prompt shown or not, error text, system version, and User-Agent if visible). Opening the portal from the system prompt confirms portal access; it does not by itself confirm diagnostic behavior or report persistence on the console.
