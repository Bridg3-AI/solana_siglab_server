#!/bin/bash

# Firebase deployment script following 2025 best practices
# Usage: ./scripts/deploy.sh [environment]

set -e

ENVIRONMENT=${1:-development}
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "🚀 Deploying Solana SigLab Server to $ENVIRONMENT environment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Firebase CLI
    if ! command -v firebase &> /dev/null; then
        log_error "Firebase CLI not found. Please install: npm install -g firebase-tools"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Check if logged in to Firebase
    if ! firebase projects:list &> /dev/null; then
        log_error "Not logged in to Firebase. Please run: firebase login"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✅"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Install Node.js dependencies for Firebase tools
    if [ -f "package.json" ]; then
        npm install
    fi
    
    # Install Python dependencies for functions
    if [ -f "src/requirements.txt" ]; then
        cd src
        python3 -m pip install -r requirements.txt
        cd ..
    fi
    
    # Install agent dependencies
    if [ -f "agents/requirements.txt" ]; then
        cd agents
        python3 -m pip install -r requirements.txt
        cd ..
    fi
    
    log_info "Dependencies installed ✅"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Python tests
    if [ -d "tests" ]; then
        python3 -m pytest tests/ -v
    else
        log_warn "No tests directory found, skipping tests"
    fi
    
    log_info "Tests completed ✅"
}

# Set Firebase project
set_firebase_project() {
    log_info "Setting Firebase project for environment: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        production)
            firebase use solana-siglab
            ;;
        staging)
            firebase use solana-siglab-staging
            ;;
        development|dev)
            firebase use solana-siglab-dev
            ;;
        *)
            log_warn "Unknown environment: $ENVIRONMENT, using default"
            firebase use default
            ;;
    esac
    
    log_info "Firebase project set ✅"
}

# Deploy functions
deploy_functions() {
    log_info "Deploying Cloud Functions..."
    
    # Deploy with specific configuration
    firebase deploy --only functions \
        --force \
        --project $(firebase use)
    
    log_info "Functions deployed ✅"
}

# Deploy Firestore rules and indexes
deploy_firestore() {
    log_info "Deploying Firestore rules and indexes..."
    
    firebase deploy --only firestore \
        --project $(firebase use)
    
    log_info "Firestore rules and indexes deployed ✅"
}

# Deploy Storage rules
deploy_storage() {
    log_info "Deploying Storage rules..."
    
    firebase deploy --only storage \
        --project $(firebase use)
    
    log_info "Storage rules deployed ✅"
}

# Deploy hosting (documentation)
deploy_hosting() {
    log_info "Deploying documentation hosting..."
    
    firebase deploy --only hosting \
        --project $(firebase use)
    
    log_info "Documentation deployed ✅"
}

# Health check after deployment
health_check() {
    log_info "Performing health check..."
    
    PROJECT_ID=$(firebase use)
    HEALTH_URL="https://${REGION:-us-central1}-${PROJECT_ID}.cloudfunctions.net/health_check"
    
    log_info "Checking health endpoint: $HEALTH_URL"
    
    # Wait a bit for deployment to propagate
    sleep 10
    
    if curl -s -f "$HEALTH_URL" > /dev/null; then
        log_info "Health check passed ✅"
    else
        log_warn "Health check failed - this might be normal for new deployments"
    fi
}

# Main deployment flow
main() {
    cd "$PROJECT_ROOT"
    
    log_info "Starting deployment process..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Environment: $ENVIRONMENT"
    
    check_prerequisites
    install_dependencies
    
    # Skip tests in production for faster deployment
    if [ "$ENVIRONMENT" != "production" ]; then
        run_tests
    fi
    
    set_firebase_project
    
    # Deploy in order
    deploy_firestore
    deploy_storage
    deploy_functions
    deploy_hosting
    
    health_check
    
    log_info "🎉 Deployment completed successfully!"
    log_info "Project: $(firebase use)"
    log_info "Environment: $ENVIRONMENT"
}

# Run main function
main "$@"