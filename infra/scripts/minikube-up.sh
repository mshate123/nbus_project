#!/usr/bin/env bash
# Bootstrap local Minikube cluster for nbus-ledger
set -euo pipefail

CLUSTER_NAME="nbus-ledger"
NAMESPACE="nbus-ledger"

echo "==> Starting Minikube cluster: $CLUSTER_NAME"
minikube start \
  --profile "$CLUSTER_NAME" \
  --cpus 2 \
  --memory 4096 \
  --driver docker

echo "==> Applying namespace"
kubectl apply -f "$(dirname "$0")/../k8s/namespace.yaml" --context "minikube-$CLUSTER_NAME"

echo "==> Cluster ready. Current context:"
kubectl config current-context

echo ""
echo "To use this cluster:"
echo "  kubectl config use-context minikube-$CLUSTER_NAME"
echo "  kubectl get all -n $NAMESPACE"
