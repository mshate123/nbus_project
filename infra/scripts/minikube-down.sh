#!/usr/bin/env bash
# Tear down local Minikube cluster for nbus-ledger
set -euo pipefail

CLUSTER_NAME="nbus-ledger"

echo "==> Stopping Minikube cluster: $CLUSTER_NAME"
minikube stop --profile "$CLUSTER_NAME"

echo "==> Done. To delete the cluster entirely:"
echo "  minikube delete --profile $CLUSTER_NAME"
