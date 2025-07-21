#!/bin/bash

# Smart Contract Deployment Script
# Automates the deployment of Solana insurance contracts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROGRAMS_DIR="$PROJECT_ROOT/programs"
KEYS_DIR="$PROJECT_ROOT/.keys"
LOGS_DIR="$PROJECT_ROOT/logs"

# Default values
CLUSTER="devnet"
PROGRAM_NAME="insurance-contract"
KEYPAIR_PATH="$KEYS_DIR/deploy-keypair.json"
RPC_URL=""
SKIP_BUILD=false
SKIP_TESTS=false
VERBOSE=false

# Ensure directories exist
mkdir -p "$KEYS_DIR"
mkdir -p "$LOGS_DIR"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOGS_DIR/deploy-$(date +%Y%m%d).log"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOGS_DIR/deploy-$(date +%Y%m%d).log"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOGS_DIR/deploy-$(date +%Y%m%d).log"
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Solana insurance smart contracts

OPTIONS:
    -c, --cluster CLUSTER     Target cluster (localnet|devnet|testnet|mainnet-beta) [default: devnet]
    -p, --program PROGRAM     Program name to deploy [default: insurance-contract]
    -k, --keypair KEYPAIR     Path to deployment keypair [default: .keys/deploy-keypair.json]
    -r, --rpc-url URL         Custom RPC URL
    --skip-build             Skip building the program
    --skip-tests             Skip running tests
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

EXAMPLES:
    $0                                    # Deploy to devnet with defaults
    $0 -c mainnet-beta -p insurance-contract
    $0 --skip-build --skip-tests -v
    $0 -c localnet -r http://127.0.0.1:8899

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--cluster)
            CLUSTER="$2"
            shift 2
            ;;
        -p|--program)
            PROGRAM_NAME="$2"
            shift 2
            ;;
        -k|--keypair)
            KEYPAIR_PATH="$2"
            shift 2
            ;;
        -r|--rpc-url)
            RPC_URL="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate cluster
case $CLUSTER in
    localnet|devnet|testnet|mainnet-beta)
        ;;
    *)
        error "Invalid cluster: $CLUSTER"
        exit 1
        ;;
esac

# Set RPC URL if not provided
if [[ -z "$RPC_URL" ]]; then
    case $CLUSTER in
        localnet)
            RPC_URL="http://127.0.0.1:8899"
            ;;
        devnet)
            RPC_URL="https://api.devnet.solana.com"
            ;;
        testnet)
            RPC_URL="https://api.testnet.solana.com"
            ;;
        mainnet-beta)
            RPC_URL="https://api.mainnet-beta.solana.com"
            ;;
    esac
fi

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    # Check if Anchor is installed
    if ! command -v anchor &> /dev/null; then
        error "Anchor CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Solana CLI is installed
    if ! command -v solana &> /dev/null; then
        error "Solana CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Rust is installed
    if ! command -v cargo &> /dev/null; then
        error "Rust/Cargo is not installed. Please install it first."
        exit 1
    fi
    
    log "All dependencies are installed."
}

# Setup Solana CLI
setup_solana() {
    log "Setting up Solana CLI..."
    
    # Set cluster
    solana config set --url "$RPC_URL"
    
    # Generate keypair if it doesn't exist
    if [[ ! -f "$KEYPAIR_PATH" ]]; then
        log "Generating new keypair: $KEYPAIR_PATH"
        solana-keygen new --outfile "$KEYPAIR_PATH" --no-bip39-passphrase
    fi
    
    # Set keypair
    solana config set --keypair "$KEYPAIR_PATH"
    
    # Show configuration
    log "Solana configuration:"
    solana config get
    
    # Check balance
    BALANCE=$(solana balance --keypair "$KEYPAIR_PATH")
    log "Account balance: $BALANCE"
    
    # Request airdrop on devnet/testnet if balance is low
    if [[ "$CLUSTER" == "devnet" || "$CLUSTER" == "testnet" ]]; then
        BALANCE_NUM=$(echo "$BALANCE" | cut -d' ' -f1)
        if (( $(echo "$BALANCE_NUM < 1" | bc -l) )); then
            log "Requesting airdrop..."
            solana airdrop 2 --keypair "$KEYPAIR_PATH" || warn "Airdrop failed"
        fi
    fi
}

# Build program
build_program() {
    if [[ "$SKIP_BUILD" == true ]]; then
        log "Skipping build..."
        return
    fi
    
    log "Building program: $PROGRAM_NAME"
    
    cd "$PROJECT_ROOT"
    
    # Clean previous build
    anchor clean
    
    # Build program
    if [[ "$VERBOSE" == true ]]; then
        anchor build --program-name "$PROGRAM_NAME" -- --features no-entrypoint
    else
        anchor build --program-name "$PROGRAM_NAME" -- --features no-entrypoint > /dev/null 2>&1
    fi
    
    log "Build completed successfully."
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        log "Skipping tests..."
        return
    fi
    
    log "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run Anchor tests
    if [[ "$VERBOSE" == true ]]; then
        anchor test --skip-build --skip-local-validator
    else
        anchor test --skip-build --skip-local-validator > /dev/null 2>&1
    fi
    
    log "Tests completed successfully."
}

# Deploy program
deploy_program() {
    log "Deploying program: $PROGRAM_NAME to $CLUSTER"
    
    cd "$PROJECT_ROOT"
    
    # Get program ID
    PROGRAM_ID=$(solana address -k "target/deploy/${PROGRAM_NAME//-/_}-keypair.json")
    log "Program ID: $PROGRAM_ID"
    
    # Check if program already exists
    if solana account "$PROGRAM_ID" &> /dev/null; then
        log "Program already exists. Upgrading..."
        
        # Upgrade program
        if [[ "$VERBOSE" == true ]]; then
            solana program deploy "target/deploy/${PROGRAM_NAME//-/_}.so" --program-id "$PROGRAM_ID" --keypair "$KEYPAIR_PATH"
        else
            solana program deploy "target/deploy/${PROGRAM_NAME//-/_}.so" --program-id "$PROGRAM_ID" --keypair "$KEYPAIR_PATH" > /dev/null 2>&1
        fi
    else
        log "Deploying new program..."
        
        # Deploy new program
        if [[ "$VERBOSE" == true ]]; then
            solana program deploy "target/deploy/${PROGRAM_NAME//-/_}.so" --keypair "$KEYPAIR_PATH"
        else
            solana program deploy "target/deploy/${PROGRAM_NAME//-/_}.so" --keypair "$KEYPAIR_PATH" > /dev/null 2>&1
        fi
    fi
    
    log "Program deployed successfully!"
    log "Program ID: $PROGRAM_ID"
    
    # Save deployment info
    DEPLOYMENT_INFO="$LOGS_DIR/deployment-$(date +%Y%m%d-%H%M%S).json"
    cat > "$DEPLOYMENT_INFO" << EOF
{
    "program_name": "$PROGRAM_NAME",
    "program_id": "$PROGRAM_ID",
    "cluster": "$CLUSTER",
    "rpc_url": "$RPC_URL",
    "deployer_keypair": "$KEYPAIR_PATH",
    "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "deployment_signature": "$(solana transaction-history --limit 1 --output json | jq -r '.[0].signature')"
}
EOF
    
    log "Deployment info saved to: $DEPLOYMENT_INFO"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Get program ID
    PROGRAM_ID=$(solana address -k "target/deploy/${PROGRAM_NAME//-/_}-keypair.json")
    
    # Check if program exists
    if solana account "$PROGRAM_ID" &> /dev/null; then
        log "✓ Program exists on $CLUSTER"
        
        # Get account info
        ACCOUNT_INFO=$(solana account "$PROGRAM_ID" --output json)
        EXECUTABLE=$(echo "$ACCOUNT_INFO" | jq -r '.executable')
        OWNER=$(echo "$ACCOUNT_INFO" | jq -r '.owner')
        
        if [[ "$EXECUTABLE" == "true" ]]; then
            log "✓ Program is executable"
        else
            error "✗ Program is not executable"
            exit 1
        fi
        
        if [[ "$OWNER" == "BPFLoaderUpgradeab1e11111111111111111111111" ]]; then
            log "✓ Program owner is correct"
        else
            warn "! Program owner is unexpected: $OWNER"
        fi
        
        log "Deployment verification completed successfully!"
    else
        error "✗ Program not found on $CLUSTER"
        exit 1
    fi
}

# Initialize program (optional)
initialize_program() {
    log "Initializing program state..."
    
    # This would call the initialize instruction on the deployed program
    # For now, we'll just log that this step would happen
    log "Program initialization would happen here..."
    log "This includes setting up initial state, admin accounts, etc."
}

# Generate SDK
generate_sdk() {
    log "Generating TypeScript SDK..."
    
    cd "$PROJECT_ROOT"
    
    # Generate IDL
    anchor idl init --filepath "target/idl/${PROGRAM_NAME//-/_}.json" "$(solana address -k "target/deploy/${PROGRAM_NAME//-/_}-keypair.json")"
    
    # Generate TypeScript types
    anchor ts
    
    log "SDK generated successfully!"
}

# Main deployment flow
main() {
    log "Starting deployment process..."
    log "Cluster: $CLUSTER"
    log "Program: $PROGRAM_NAME"
    log "RPC URL: $RPC_URL"
    log "Keypair: $KEYPAIR_PATH"
    
    check_dependencies
    setup_solana
    build_program
    run_tests
    deploy_program
    verify_deployment
    initialize_program
    generate_sdk
    
    log "Deployment completed successfully! 🎉"
    log "Program ID: $(solana address -k "target/deploy/${PROGRAM_NAME//-/_}-keypair.json")"
    log "Cluster: $CLUSTER"
    log "Explorer: https://explorer.solana.com/address/$(solana address -k "target/deploy/${PROGRAM_NAME//-/_}-keypair.json")?cluster=$CLUSTER"
}

# Run main function
main "$@"