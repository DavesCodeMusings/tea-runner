Use the Dockerfile in this directory to test building a Docker container when changes are committed.

Tea Runner must be running on the destination host (<server_name_or_ip> below).

1. Create a Gitea repository called hello-docker.
2. Add the Dockerfile found in this directoy to the Gitea repository.
3. Configure a webhook in the repository with a target URL of http://<server_name_or_ip>:1706/docker/build
4. Trigger the webhook with Gitea's Test Delivery button.
5. Verify the image is on the destination host by running: docker run --rm hello-docker
