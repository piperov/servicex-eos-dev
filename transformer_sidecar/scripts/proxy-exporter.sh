echo "INFO proxy-exporter: X509_USER_PROXY='${X509_USER_PROXY}'"

if [[ "${X509_USER_PROXY}" == "/etc/grid-security-ro/x509up" ]] || [[ -z "${X509_USER_PROXY}" ]]; then
    echo "INFO proxy-exporter: X509_USER_PROXY unset or points to read-only mount — resetting to /tmp/grid-security/x509up"
    export X509_USER_PROXY="/tmp/grid-security/x509up"
fi

echo "INFO proxy-exporter: Final X509_USER_PROXY=${X509_USER_PROXY}"

proxydir=$(dirname ${X509_USER_PROXY})
echo "INFO proxy-exporter: proxy directory will be ${proxydir}"

if [[ ! -d $proxydir ]]; then
    echo "INFO proxy-exporter: Creating proxy directory ${proxydir}"
    mkdir -p $proxydir
fi

echo "INFO proxy-exporter: Checking source proxy at /etc/grid-security-ro/x509up ..."
if [[ -f /etc/grid-security-ro/x509up ]]; then
    echo "INFO proxy-exporter: Source proxy EXISTS: $(ls -la /etc/grid-security-ro/x509up)"
else
    echo "WARNING proxy-exporter: Source proxy /etc/grid-security-ro/x509up does NOT exist! x509 Secret may not be mounted."
    ls -la /etc/grid-security-ro/ 2>&1 || echo "WARNING proxy-exporter: /etc/grid-security-ro/ is also missing!"
fi

while true; do

    while true; do
        cp /etc/grid-security-ro/x509up ${X509_USER_PROXY}
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "INFO $INSTANCE_NAME proxy-exporter: Got proxy successfully."
            chown 1001:1001 ${X509_USER_PROXY} || true
            chmod 600 ${X509_USER_PROXY}
            echo "INFO proxy-exporter: Proxy file at destination: $(ls -la ${X509_USER_PROXY})"
            id
            break
        else
            echo "WARNING $INSTANCE_NAME proxy-exporter: Copy failed (exit=$RESULT). Retrying in 5s ..."
            sleep 5
        fi
    done

   # Refresh every hour
   echo "INFO proxy-exporter: Proxy refreshed. Next refresh in 3600s."
   sleep 3600

done
