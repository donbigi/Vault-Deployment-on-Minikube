# HashiCorp Vault Deployment on Minikube Using Helm

This guide provides step-by-step instructions for deploying HashiCorp Vault using Helm on a minikube, I w also create a docker image which we will use to retrieve the contents of Vault

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Vault Installation and Config](#vault-installation-and-config)
3. [Webapp Deployment](#webapp-deployment)
4. [Configure HashiCorp Vault](#configure-hashicorp-vault) 

## Prerequisites

- Docker
  Download from [here](https://docs.docker.com/get-docker/).

- Minikube
  Download and install Minikube from [here](https://minikube.sigs.k8s.io/docs/start/).

## Vault Installation and Config

1. **Install the Vault Helm Chart**
2. **Create Policy**
3. **Create a Secret Engine in Vault**
4. **Configure Kubernetes Authentication**
5. **Create a Role**

Download and install Helm from [here](https://helm.sh/docs/intro/install/).

Install Vault with Integrated Storage
```bash
# Source: https://artifacthub.io/packages/helm/hashicorp/vault
helm repo add hashicorp https://helm.releases.hashicorp.com


# Install Vault Helm chart with Integrated Storage
cat > helm-vault-raft-values.yml <<EOF
server:
  affinity: ""
  ha:
    enabled: true
    raft: 
      enabled: true
EOF

# Create namespace vault and installs vaults there
helm install vault hashicorp/vault --values helm-vault-raft-values.yml --create-namespace -n vault
```

This creates three Vault server instances with an Integrated Storage (Raft) backend.

Initialize vault-0 with one key share and one key threshold.
```bash
kubectl exec vault-0 -n vault -- vault operator init > cluster-keys.text
cat cluster-keys.text
```

Create a variables named ```VAULT_UNSEAL_KEY_1```, ```VAULT_UNSEAL_KEY_2```, ```VAULT_UNSEAL_KEY_3``` to capture the Vault unseal key

```bash
VAULT_UNSEAL_KEY_1=KEY_1
VAULT_UNSEAL_KEY_2=KEY_2
VAULT_UNSEAL_KEY_3=KEY_3
```
Unseal Vault running on the vault-0 pod
```bash
kubectl exec -it vault-0 -n vault -- sh

vault operator unseal
$VAULT_UNSEAL_KEY_1

vault operator unseal
$VAULT_UNSEAL_KEY_2

vault operator unseal
$VAULT_UNSEAL_KEY_3
```

Join the vault-1 and vault-2pods to the Raft cluster
```bash
kubectl exec -it vault-1 -n vault -- vault operator raft join http://vault-0.vault-internal:8200
kubectl exec -it vault-2 -n vault -- vault operator raft join http://vault-0.vault-internal:8200
```

Use the unseal key from above to unseal ```vault-1``` and ```vault-2```

```bash
kubectl exec -it vault-1 -n vault -- sh

vault operator unseal
$VAULT_UNSEAL_KEY_1

vault operator unseal
$VAULT_UNSEAL_KEY_2

vault operator unseal
$VAULT_UNSEAL_KEY_3
```

```bash
kubectl exec -it vault-2 -n vault -- sh

vault operator unseal
$VAULT_UNSEAL_KEY_1

vault operator unseal
$VAULT_UNSEAL_KEY_2

vault operator unseal
$VAULT_UNSEAL_KEY_3
```
After this unsealing process all vault pods are now in running (1/1 ready ) state


We can use port forwarding to access Vault service on browser
```bash
kubectl port-forward service/vault -n vault 8200:8200
```
use http://localhost:8200 in browser to access vault and enter root token

you can also use command line too to create secret, roles auth and policy.

```bash
# Start an interactive shell session on the vault-0 pod
kubectl exec --stdin=true --tty=true vault-0 -n vault -- /bin/sh
vault login
```
use your token saved earlier to enter
```
# open another terminal and run the code below to extract token
cat cluster-keys.text | grep -i token
```

Write out the policy named ```webapp``` that enables the ```read``` capability for secrets at path ```secret/data/webapp/config```

```bash
vault policy write webapp - <<EOF path "secret/data/webapp/config" {
  capabilities = ["read", "create", "update", "delete"]
} EOF
```
This policy will let us create secret.

Create a secret at path ```secret/webapp/config``` with a ```username``` and ```password```.

```bash
vault kv put secret/webapp/config username="uche" password="password_uche"
```

Verify that the secret is defined at the path ```secret/webapp/config```

```bash
vault kv get secret/webapp/config
```
Enable the Kubernetes authentication method
```bash
vault auth enable kubernetes
```
Configure the Kubernetes authentication method to use the location of the Kubernetes API.
```bash
vault write auth/kubernetes/config \
    kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443"
```

Create a Kubernetes authentication role, named webapp, that connects the Kubernetes service account name and webapp policy.

Before we do that, lets first create a service account
open a second terminal and run:
```bash
kubectl create sa webapp-service-account -n webapps
```

Go back to the other ternimal window and run
```bash
vault write auth/kubernetes/role/webapp \
        bound_service_account_names=webapp-service-account \
        bound_service_account_namespaces=webapps \
        policies=webapp \
        ttl=24h
```
The role connects the Kubernetes service account, vault, and namespace, with the Vault policy, webapp. The tokens returned after authentication are valid for 24 hours.




## Webapp Deployment

1. Create a Docker Image and push it to docker-hub
2. Deploy the webapp on kubernetes
3. Access the webapp to retrieve secret

Creating a docker image:
First create a ```app.py``` python file,Then the Dockerfile
both file are located in the ```/webapp/``` directory of this repo

Upload the docker imaage to docker hub
goto the webapp folder or where your dockerfile is
```bash
docker build -it webapp:v1 .
```

tag the docker image
```bash
docker tag webapp:v1 username/webapp:v1
```
(optional) if you are not logged into docker, run this

```bash
Docker login
```
push image to docker registry

```bash
docker push username/webapp:v1
```
now we can use the image in our deployment to test if we can access vault


Next, we want to store VAULT_TOKEN as a secret
the secret yaml file is store as ```vault-auth-token.yaml``` in this repo

use ```echo -n "TOKEN" | base64``` to convert token to base 64


Create Webapp deployment
Check the home directory of this repo for  ```webapp.yaml``` deployment.

the image we created earlier is used in the deployment

Apply the updated deployment to your Kubernetes cluster:
```bash
kubectl apply -f webapp.yaml

```

In another terminal, port forward all requests made to http://localhost:8080 to the webapp pod on port 8080.

```bash
kubectl port-forward \
 POD_OF_WEBAPP_DEPLOYMENT \
 8080:8080 -n webapps
```

So finally our sample web application running on port 8080 in the webapp pod is able to ,

authenticates with the Kubernetes service account token
receives a Vault token with the read capability at the ```secret/data/webapp/config``` path
retrieves the secrets from ```secret/data/webapp/config``` path
displays the secrets 

Thank you for reading
