Use the index.html file in this directory to test rsync of files when changes are committed.

Tea Runner must be running on the destination host (<server_name_or_ip> below). You will also need a /srv/www directory on the destination host.

1. Create a Gitea repository called hello-www.
2. Add the index.html file found in this directoy to the Gitea repository.
3. Configure a webhook in the repository with a target URL of http://<server_name_or_ip>:1706/rsync?dest=%2Fsrv%2Fwww
4. Trigger the webhook with Gitea's Test Delivery button.
5. Verify the index.html file is on the destination host by running: cat /srv/www/index.html

See also: https://docs.gitea.io/en-us/webhooks/
