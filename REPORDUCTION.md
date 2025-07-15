# 0. Preparation
If you are on Windows, use WSL Ubuntu.
## Install Docker
https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
Make sure you do the post-install steps.
```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo docker run hello-world

sudo groupadd docker

sudo usermod -aG docker $USER

newgrp docker

docker run hello-world
```

## Install Minikube
https://minikube.sigs.k8s.io/docs/start/?arch=%2Flinux%2Fx86-64%2Fstable%2Fbinary+download
```bash
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
```

## Install Kubectl
https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

kubectl version --client

kubectl get po -A
```

## Install Istio
https://istio.io/latest/docs/ambient/getting-started/
```bash
cd ~
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.26.0
export PATH=$PWD/bin:$PATH # add this to bashrc
```

## Setup Minikube Cluster
```bash
minikube start -p tea-store --cpus 6 --memory 6000 --addons=metrics-server # minikube addons enable metrics-server
minikube profile tea-store

# Install Istio in cluster
istioctl install --set profile=demo -y
kubectl label namespace default istio-injection=enabled
kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null || \
{ kubectl kustomize "github.com/kubernetes-sigs/gateway-api/config/crd?ref=v1.3.0-rc.1" | kubectl apply -f -; }
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.26/samples/addons/grafana.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.26/samples/addons/prometheus.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.26/samples/addons/kiali.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.26/samples/addons/jaeger.yaml

# Build Images
eval $(minikube docker-env)
bash build-docker.sh
```

# 1. Run basic Teastore
## Start minikube cluster (if stopped before)
```bash
minikube profile tea-store
minikube start 
```

## Start TeaStore
```bash
kubectl apply -f teastore-kube.yaml # modified, add the gateway for metrics
minikube tunnel # start gateway
# goto http://localhost to see the page (private window suggested to prevent old cookies)
```

## Start Dashboard
```bash
istioctl dashboard grafana
istioctl dashboard kiali
istioctl dashboard jaeger
```

