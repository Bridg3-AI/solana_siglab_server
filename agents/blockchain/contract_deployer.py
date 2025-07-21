"""Smart contract deployment and management"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
import json
import base64
from pathlib import Path
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import create_account, CreateAccountParams
from .solana_client import SolanaClient
from .token_manager import TokenManager
from .oracle_client import OracleClient
from ..core.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class ContractTemplate:
    """Smart contract template"""
    name: str
    description: str
    template_type: str  # parametric_insurance, token_distribution, oracle_feed
    parameters: Dict[str, Any]
    bytecode: Optional[str]
    abi: Optional[Dict[str, Any]]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'template_type': self.template_type,
            'parameters': self.parameters,
            'bytecode': self.bytecode,
            'abi': self.abi,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class DeployedContract:
    """Deployed contract information"""
    contract_id: str
    program_id: str
    name: str
    template_type: str
    parameters: Dict[str, Any]
    deployer: str
    deployment_signature: str
    deployed_at: datetime
    status: str  # active, paused, terminated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'contract_id': self.contract_id,
            'program_id': self.program_id,
            'name': self.name,
            'template_type': self.template_type,
            'parameters': self.parameters,
            'deployer': self.deployer,
            'deployment_signature': self.deployment_signature,
            'deployed_at': self.deployed_at.isoformat(),
            'status': self.status
        }

@dataclass
class InsurancePolicy:
    """Insurance policy data structure"""
    policy_id: str
    contract_address: str
    policy_holder: str
    coverage_amount: float
    premium_amount: float
    policy_type: str  # weather, flight, crypto
    trigger_conditions: Dict[str, Any]
    expiry_date: datetime
    status: str  # active, expired, claimed
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'policy_id': self.policy_id,
            'contract_address': self.contract_address,
            'policy_holder': self.policy_holder,
            'coverage_amount': self.coverage_amount,
            'premium_amount': self.premium_amount,
            'policy_type': self.policy_type,
            'trigger_conditions': self.trigger_conditions,
            'expiry_date': self.expiry_date.isoformat(),
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class ContractDeployer:
    """Smart contract deployment and management"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        self.token_manager = TokenManager(cluster)
        self.oracle_client = OracleClient(cluster)
        
        # Contract templates directory
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Deployed contracts registry
        self.deployed_contracts: Dict[str, DeployedContract] = {}
        
        # Insurance policies registry
        self.insurance_policies: Dict[str, InsurancePolicy] = {}
    
    def get_contract_templates(self) -> List[ContractTemplate]:
        """Get available contract templates"""
        templates = []
        
        # Weather insurance template
        weather_template = ContractTemplate(
            name="Weather Insurance",
            description="Parametric weather insurance contract",
            template_type="parametric_insurance",
            parameters={
                "location": "string",
                "weather_event": "string",  # typhoon, earthquake, flood
                "trigger_threshold": "float",
                "coverage_amount": "float",
                "premium_rate": "float",
                "duration_days": "integer"
            },
            bytecode=None,  # Would contain actual bytecode
            abi=None,  # Would contain actual ABI
            created_at=datetime.now()
        )
        templates.append(weather_template)
        
        # Flight insurance template
        flight_template = ContractTemplate(
            name="Flight Insurance",
            description="Flight delay insurance contract",
            template_type="parametric_insurance",
            parameters={
                "flight_number": "string",
                "departure_date": "datetime",
                "delay_threshold_minutes": "integer",
                "coverage_amount": "float",
                "premium_rate": "float"
            },
            bytecode=None,
            abi=None,
            created_at=datetime.now()
        )
        templates.append(flight_template)
        
        # Crypto insurance template
        crypto_template = ContractTemplate(
            name="Crypto Insurance",
            description="Cryptocurrency volatility insurance contract",
            template_type="parametric_insurance",
            parameters={
                "crypto_symbol": "string",
                "volatility_threshold": "float",
                "coverage_amount": "float",
                "premium_rate": "float",
                "duration_days": "integer"
            },
            bytecode=None,
            abi=None,
            created_at=datetime.now()
        )
        templates.append(crypto_template)
        
        return templates
    
    async def deploy_contract(self, template: ContractTemplate,
                            parameters: Dict[str, Any],
                            deployer: Keypair,
                            contract_name: str) -> DeployedContract:
        """Deploy a smart contract from template"""
        try:
            # Generate contract keypair
            contract_keypair = Keypair()
            
            # Create mock deployment for development
            # In production, this would deploy actual Anchor program
            deployment_signature = await self._deploy_mock_contract(
                contract_keypair, deployer, template, parameters
            )
            
            # Create deployed contract record
            contract_id = self._generate_contract_id(contract_name, template.template_type)
            
            deployed_contract = DeployedContract(
                contract_id=contract_id,
                program_id=str(contract_keypair.public_key),
                name=contract_name,
                template_type=template.template_type,
                parameters=parameters,
                deployer=str(deployer.public_key),
                deployment_signature=deployment_signature,
                deployed_at=datetime.now(),
                status="active"
            )
            
            # Store in registry
            self.deployed_contracts[contract_id] = deployed_contract
            
            logger.info(f"Deployed contract: {contract_name} ({contract_id})")
            
            return deployed_contract
            
        except Exception as e:
            logger.error(f"Error deploying contract: {e}")
            raise
    
    async def _deploy_mock_contract(self, contract_keypair: Keypair,
                                  deployer: Keypair,
                                  template: ContractTemplate,
                                  parameters: Dict[str, Any]) -> str:
        """Deploy mock contract for development"""
        try:
            async with SolanaClient(self.cluster) as client:
                # Create a simple account to represent the contract
                rent_response = await client.client.get_minimum_balance_for_rent_exemption(1000)
                min_rent = rent_response.value
                
                # Create account instruction
                create_account_instruction = create_account(
                    CreateAccountParams(
                        from_pubkey=deployer.public_key,
                        new_account_pubkey=contract_keypair.public_key,
                        lamports=min_rent,
                        space=1000,
                        program_id=deployer.public_key  # Mock program ID
                    )
                )
                
                # Create transaction
                transaction = Transaction()
                transaction.add(create_account_instruction)
                
                # Send transaction
                signature = await client.send_transaction(transaction, [deployer, contract_keypair])
                
                # Wait for confirmation
                confirmed = await client.wait_for_confirmation(signature)
                
                if confirmed:
                    logger.info(f"Mock contract deployed: {contract_keypair.public_key}")
                    return signature
                else:
                    raise Exception("Mock contract deployment failed")
                    
        except Exception as e:
            logger.error(f"Error deploying mock contract: {e}")
            raise
    
    def _generate_contract_id(self, name: str, template_type: str) -> str:
        """Generate unique contract ID"""
        import hashlib
        import uuid
        
        # Create unique ID based on name, type, and timestamp
        data = f"{name}_{template_type}_{datetime.now().isoformat()}_{uuid.uuid4()}"
        contract_id = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        return f"{template_type}_{contract_id}"
    
    async def create_insurance_policy(self, contract_id: str,
                                    policy_holder: str,
                                    coverage_amount: float,
                                    premium_amount: float,
                                    trigger_conditions: Dict[str, Any],
                                    duration_days: int = 30) -> InsurancePolicy:
        """Create a new insurance policy"""
        try:
            # Get deployed contract
            contract = self.deployed_contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Contract not found: {contract_id}")
            
            # Generate policy ID
            policy_id = self._generate_policy_id(contract_id, policy_holder)
            
            # Calculate expiry date
            expiry_date = datetime.now() + timedelta(days=duration_days)
            
            # Create insurance policy
            policy = InsurancePolicy(
                policy_id=policy_id,
                contract_address=contract.program_id,
                policy_holder=policy_holder,
                coverage_amount=coverage_amount,
                premium_amount=premium_amount,
                policy_type=contract.template_type,
                trigger_conditions=trigger_conditions,
                expiry_date=expiry_date,
                status="active",
                created_at=datetime.now()
            )
            
            # Store in registry
            self.insurance_policies[policy_id] = policy
            
            logger.info(f"Created insurance policy: {policy_id}")
            
            return policy
            
        except Exception as e:
            logger.error(f"Error creating insurance policy: {e}")
            raise
    
    def _generate_policy_id(self, contract_id: str, policy_holder: str) -> str:
        """Generate unique policy ID"""
        import hashlib
        import uuid
        
        data = f"{contract_id}_{policy_holder}_{datetime.now().isoformat()}_{uuid.uuid4()}"
        policy_id = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        return f"policy_{policy_id}"
    
    async def check_trigger_conditions(self, policy_id: str) -> Dict[str, Any]:
        """Check if policy trigger conditions are met"""
        try:
            policy = self.insurance_policies.get(policy_id)
            if not policy:
                raise ValueError(f"Policy not found: {policy_id}")
            
            if policy.status != "active":
                return {
                    'policy_id': policy_id,
                    'triggered': False,
                    'reason': f'Policy status is {policy.status}',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check expiry
            if datetime.now() > policy.expiry_date:
                return {
                    'policy_id': policy_id,
                    'triggered': False,
                    'reason': 'Policy expired',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check conditions based on policy type
            if policy.policy_type == "weather":
                return await self._check_weather_conditions(policy)
            elif policy.policy_type == "flight":
                return await self._check_flight_conditions(policy)
            elif policy.policy_type == "crypto":
                return await self._check_crypto_conditions(policy)
            else:
                return {
                    'policy_id': policy_id,
                    'triggered': False,
                    'reason': f'Unknown policy type: {policy.policy_type}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error checking trigger conditions: {e}")
            return {
                'policy_id': policy_id,
                'triggered': False,
                'reason': f'Error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_weather_conditions(self, policy: InsurancePolicy) -> Dict[str, Any]:
        """Check weather-related trigger conditions"""
        try:
            from ..data.weather import get_weather_risk_analysis
            
            conditions = policy.trigger_conditions
            location = conditions.get('location')
            event_type = conditions.get('weather_event')
            threshold = conditions.get('trigger_threshold')
            
            # Get weather risk analysis
            risk_analysis = await get_weather_risk_analysis(location, event_type)
            
            # Check if risk score exceeds threshold
            triggered = risk_analysis['risk_score'] >= threshold
            
            return {
                'policy_id': policy.policy_id,
                'triggered': triggered,
                'current_risk_score': risk_analysis['risk_score'],
                'threshold': threshold,
                'location': location,
                'event_type': event_type,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking weather conditions: {e}")
            return {
                'policy_id': policy.policy_id,
                'triggered': False,
                'reason': f'Weather check error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_flight_conditions(self, policy: InsurancePolicy) -> Dict[str, Any]:
        """Check flight-related trigger conditions"""
        try:
            from ..data.flight import get_flight_risk_analysis
            
            conditions = policy.trigger_conditions
            flight_number = conditions.get('flight_number')
            delay_threshold = conditions.get('delay_threshold_minutes')
            
            # Get flight risk analysis
            risk_analysis = await get_flight_risk_analysis(flight_number)
            
            # Check if delay exceeds threshold
            flight_data = risk_analysis.get('risk_factors', {}).get('flight_data', {})
            delay_minutes = flight_data.get('delay_minutes', 0)
            
            triggered = delay_minutes >= delay_threshold
            
            return {
                'policy_id': policy.policy_id,
                'triggered': triggered,
                'current_delay': delay_minutes,
                'threshold': delay_threshold,
                'flight_number': flight_number,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking flight conditions: {e}")
            return {
                'policy_id': policy.policy_id,
                'triggered': False,
                'reason': f'Flight check error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _check_crypto_conditions(self, policy: InsurancePolicy) -> Dict[str, Any]:
        """Check crypto-related trigger conditions"""
        try:
            from ..data.crypto import get_crypto_risk_analysis
            
            conditions = policy.trigger_conditions
            crypto_symbol = conditions.get('crypto_symbol')
            volatility_threshold = conditions.get('volatility_threshold')
            
            # Get crypto risk analysis
            risk_analysis = await get_crypto_risk_analysis([crypto_symbol])
            
            # Check if volatility exceeds threshold
            individual_risks = risk_analysis.get('individual_risks', {})
            crypto_risk = individual_risks.get(crypto_symbol, {})
            volatility = crypto_risk.get('volatility', 0)
            
            triggered = volatility >= volatility_threshold
            
            return {
                'policy_id': policy.policy_id,
                'triggered': triggered,
                'current_volatility': volatility,
                'threshold': volatility_threshold,
                'crypto_symbol': crypto_symbol,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking crypto conditions: {e}")
            return {
                'policy_id': policy.policy_id,
                'triggered': False,
                'reason': f'Crypto check error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def process_claim(self, policy_id: str, 
                          payout_keypair: Keypair) -> Dict[str, Any]:
        """Process insurance claim and payout"""
        try:
            # Check trigger conditions
            trigger_result = await self.check_trigger_conditions(policy_id)
            
            if not trigger_result['triggered']:
                return {
                    'policy_id': policy_id,
                    'success': False,
                    'reason': 'Trigger conditions not met',
                    'trigger_result': trigger_result,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get policy
            policy = self.insurance_policies[policy_id]
            
            # Process payout
            payout_result = await self._process_payout(policy, payout_keypair)
            
            if payout_result['success']:
                # Update policy status
                policy.status = "claimed"
                self.insurance_policies[policy_id] = policy
                
                logger.info(f"Claim processed successfully: {policy_id}")
            
            return {
                'policy_id': policy_id,
                'success': payout_result['success'],
                'payout_amount': policy.coverage_amount,
                'payout_signature': payout_result.get('signature'),
                'trigger_result': trigger_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing claim: {e}")
            return {
                'policy_id': policy_id,
                'success': False,
                'reason': f'Claim processing error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _process_payout(self, policy: InsurancePolicy,
                            payout_keypair: Keypair) -> Dict[str, Any]:
        """Process payout to policy holder"""
        try:
            # For simplicity, use SOL transfer
            # In production, this would use insurance token or USDC
            
            async with SolanaClient(self.cluster) as client:
                signature = await client.transfer_sol(
                    from_keypair=payout_keypair,
                    to_address=policy.policy_holder,
                    amount=policy.coverage_amount
                )
                
                return {
                    'success': True,
                    'signature': signature,
                    'amount': policy.coverage_amount,
                    'recipient': policy.policy_holder
                }
                
        except Exception as e:
            logger.error(f"Error processing payout: {e}")
            return {
                'success': False,
                'reason': f'Payout error: {str(e)}'
            }
    
    def get_deployed_contracts(self) -> List[DeployedContract]:
        """Get all deployed contracts"""
        return list(self.deployed_contracts.values())
    
    def get_insurance_policies(self) -> List[InsurancePolicy]:
        """Get all insurance policies"""
        return list(self.insurance_policies.values())
    
    def get_contract_by_id(self, contract_id: str) -> Optional[DeployedContract]:
        """Get contract by ID"""
        return self.deployed_contracts.get(contract_id)
    
    def get_policy_by_id(self, policy_id: str) -> Optional[InsurancePolicy]:
        """Get policy by ID"""
        return self.insurance_policies.get(policy_id)
    
    def get_policies_by_holder(self, policy_holder: str) -> List[InsurancePolicy]:
        """Get policies by holder address"""
        return [
            policy for policy in self.insurance_policies.values()
            if policy.policy_holder == policy_holder
        ]
    
    async def get_contract_statistics(self) -> Dict[str, Any]:
        """Get contract deployment statistics"""
        total_contracts = len(self.deployed_contracts)
        active_contracts = sum(1 for c in self.deployed_contracts.values() if c.status == "active")
        
        total_policies = len(self.insurance_policies)
        active_policies = sum(1 for p in self.insurance_policies.values() if p.status == "active")
        claimed_policies = sum(1 for p in self.insurance_policies.values() if p.status == "claimed")
        
        # Calculate total coverage and premiums
        total_coverage = sum(p.coverage_amount for p in self.insurance_policies.values())
        total_premiums = sum(p.premium_amount for p in self.insurance_policies.values())
        
        return {
            'contracts': {
                'total': total_contracts,
                'active': active_contracts,
                'paused': sum(1 for c in self.deployed_contracts.values() if c.status == "paused"),
                'terminated': sum(1 for c in self.deployed_contracts.values() if c.status == "terminated")
            },
            'policies': {
                'total': total_policies,
                'active': active_policies,
                'claimed': claimed_policies,
                'expired': sum(1 for p in self.insurance_policies.values() if p.status == "expired")
            },
            'financials': {
                'total_coverage': total_coverage,
                'total_premiums': total_premiums,
                'claim_ratio': claimed_policies / total_policies if total_policies > 0 else 0
            },
            'timestamp': datetime.now().isoformat()
        }


# Convenience functions for direct use
async def deploy_weather_insurance(deployer: Keypair,
                                 location: str,
                                 weather_event: str,
                                 trigger_threshold: float,
                                 coverage_amount: float,
                                 premium_rate: float,
                                 cluster: str = "mainnet-beta") -> DeployedContract:
    """Deploy weather insurance contract"""
    contract_deployer = ContractDeployer(cluster)
    templates = contract_deployer.get_contract_templates()
    
    weather_template = next(t for t in templates if t.name == "Weather Insurance")
    
    parameters = {
        "location": location,
        "weather_event": weather_event,
        "trigger_threshold": trigger_threshold,
        "coverage_amount": coverage_amount,
        "premium_rate": premium_rate,
        "duration_days": 30
    }
    
    return await contract_deployer.deploy_contract(
        template=weather_template,
        parameters=parameters,
        deployer=deployer,
        contract_name=f"Weather Insurance - {location}"
    )

async def create_weather_policy(contract_id: str,
                              policy_holder: str,
                              coverage_amount: float,
                              premium_amount: float,
                              location: str,
                              weather_event: str,
                              trigger_threshold: float,
                              cluster: str = "mainnet-beta") -> InsurancePolicy:
    """Create weather insurance policy"""
    contract_deployer = ContractDeployer(cluster)
    
    trigger_conditions = {
        "location": location,
        "weather_event": weather_event,
        "trigger_threshold": trigger_threshold
    }
    
    return await contract_deployer.create_insurance_policy(
        contract_id=contract_id,
        policy_holder=policy_holder,
        coverage_amount=coverage_amount,
        premium_amount=premium_amount,
        trigger_conditions=trigger_conditions
    )