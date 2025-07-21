//! Parametric Insurance Smart Contract for Solana
//! 
//! This contract implements parametric insurance policies that automatically
//! pay out based on predefined conditions and oracle data feeds.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use pyth_sdk_solana::load_price_feed_from_account_info;

declare_id!("InsuranceContract1111111111111111111111111111");

#[program]
pub mod insurance_contract {
    use super::*;

    /// Initialize a new insurance contract
    pub fn initialize(
        ctx: Context<Initialize>,
        bump: u8,
        oracle_address: Pubkey,
        trigger_threshold: i64,
        coverage_amount: u64,
        premium_amount: u64,
        expiry_timestamp: i64,
    ) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        let clock = Clock::get()?;

        insurance_policy.authority = ctx.accounts.authority.key();
        insurance_policy.policy_holder = ctx.accounts.policy_holder.key();
        insurance_policy.oracle_address = oracle_address;
        insurance_policy.trigger_threshold = trigger_threshold;
        insurance_policy.coverage_amount = coverage_amount;
        insurance_policy.premium_amount = premium_amount;
        insurance_policy.expiry_timestamp = expiry_timestamp;
        insurance_policy.created_timestamp = clock.unix_timestamp;
        insurance_policy.status = PolicyStatus::Active;
        insurance_policy.bump = bump;

        msg!("Insurance policy initialized: {}", insurance_policy.key());
        Ok(())
    }

    /// Purchase insurance policy by paying premium
    pub fn purchase_policy(ctx: Context<PurchasePolicy>) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        let clock = Clock::get()?;

        // Check if policy is still active and not expired
        require!(
            insurance_policy.status == PolicyStatus::Active,
            InsuranceError::PolicyNotActive
        );
        require!(
            clock.unix_timestamp < insurance_policy.expiry_timestamp,
            InsuranceError::PolicyExpired
        );

        // Transfer premium from policy holder to insurance pool
        let cpi_accounts = Transfer {
            from: ctx.accounts.policy_holder_token_account.to_account_info(),
            to: ctx.accounts.insurance_pool_token_account.to_account_info(),
            authority: ctx.accounts.policy_holder.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        
        token::transfer(cpi_ctx, insurance_policy.premium_amount)?;

        insurance_policy.status = PolicyStatus::Purchased;
        insurance_policy.purchased_timestamp = Some(clock.unix_timestamp);

        msg!("Policy purchased: {}", insurance_policy.key());
        Ok(())
    }

    /// Check oracle conditions and trigger payout if conditions are met
    pub fn check_trigger_conditions(ctx: Context<CheckTriggerConditions>) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        let clock = Clock::get()?;

        // Check if policy is purchased and not expired
        require!(
            insurance_policy.status == PolicyStatus::Purchased,
            InsuranceError::PolicyNotPurchased
        );
        require!(
            clock.unix_timestamp < insurance_policy.expiry_timestamp,
            InsuranceError::PolicyExpired
        );

        // Load oracle price data
        let oracle_account_info = &ctx.accounts.oracle_account;
        let price_feed = load_price_feed_from_account_info(oracle_account_info)?;
        let current_price = price_feed.get_current_price().unwrap();

        msg!("Current oracle price: {}", current_price.price);
        msg!("Trigger threshold: {}", insurance_policy.trigger_threshold);

        // Check if trigger conditions are met
        let trigger_met = match insurance_policy.trigger_condition_type() {
            TriggerConditionType::PriceAbove => current_price.price > insurance_policy.trigger_threshold,
            TriggerConditionType::PriceBelow => current_price.price < insurance_policy.trigger_threshold,
            TriggerConditionType::VolatilityAbove => {
                // Simplified volatility check - in production, would use historical data
                let price_confidence = current_price.conf as i64;
                (price_confidence * 100 / current_price.price) > insurance_policy.trigger_threshold
            }
        };

        if trigger_met {
            // Trigger payout
            insurance_policy.status = PolicyStatus::TriggeredPayout;
            insurance_policy.triggered_timestamp = Some(clock.unix_timestamp);
            insurance_policy.trigger_price = Some(current_price.price);

            msg!("Trigger conditions met! Payout triggered for policy: {}", insurance_policy.key());
        } else {
            msg!("Trigger conditions not met for policy: {}", insurance_policy.key());
        }

        Ok(())
    }

    /// Execute payout to policy holder
    pub fn execute_payout(ctx: Context<ExecutePayout>) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        let clock = Clock::get()?;

        // Check if payout was triggered
        require!(
            insurance_policy.status == PolicyStatus::TriggeredPayout,
            InsuranceError::PayoutNotTriggered
        );

        // Transfer coverage amount from insurance pool to policy holder
        let seeds = &[
            b"insurance_policy".as_ref(),
            insurance_policy.authority.as_ref(),
            insurance_policy.policy_holder.as_ref(),
            &[insurance_policy.bump],
        ];
        let signer = &[&seeds[..]];

        let cpi_accounts = Transfer {
            from: ctx.accounts.insurance_pool_token_account.to_account_info(),
            to: ctx.accounts.policy_holder_token_account.to_account_info(),
            authority: ctx.accounts.insurance_policy.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer);
        
        token::transfer(cpi_ctx, insurance_policy.coverage_amount)?;

        insurance_policy.status = PolicyStatus::PaidOut;
        insurance_policy.payout_timestamp = Some(clock.unix_timestamp);

        msg!("Payout executed for policy: {}", insurance_policy.key());
        Ok(())
    }

    /// Cancel policy and refund premium (if not yet triggered)
    pub fn cancel_policy(ctx: Context<CancelPolicy>) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        let clock = Clock::get()?;

        // Check if policy can be cancelled
        require!(
            insurance_policy.status == PolicyStatus::Purchased,
            InsuranceError::PolicyCannotBeCancelled
        );
        require!(
            clock.unix_timestamp < insurance_policy.expiry_timestamp,
            InsuranceError::PolicyExpired
        );

        // Calculate refund amount (could implement fee deduction)
        let refund_amount = insurance_policy.premium_amount;

        // Transfer refund from insurance pool to policy holder
        let seeds = &[
            b"insurance_policy".as_ref(),
            insurance_policy.authority.as_ref(),
            insurance_policy.policy_holder.as_ref(),
            &[insurance_policy.bump],
        ];
        let signer = &[&seeds[..]];

        let cpi_accounts = Transfer {
            from: ctx.accounts.insurance_pool_token_account.to_account_info(),
            to: ctx.accounts.policy_holder_token_account.to_account_info(),
            authority: ctx.accounts.insurance_policy.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer);
        
        token::transfer(cpi_ctx, refund_amount)?;

        insurance_policy.status = PolicyStatus::Cancelled;
        insurance_policy.cancelled_timestamp = Some(clock.unix_timestamp);

        msg!("Policy cancelled: {}", insurance_policy.key());
        Ok(())
    }

    /// Update oracle address (admin function)
    pub fn update_oracle(ctx: Context<UpdateOracle>, new_oracle_address: Pubkey) -> Result<()> {
        let insurance_policy = &mut ctx.accounts.insurance_policy;
        
        insurance_policy.oracle_address = new_oracle_address;
        
        msg!("Oracle address updated for policy: {}", insurance_policy.key());
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(bump: u8)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    /// CHECK: This is the policy holder address
    pub policy_holder: AccountInfo<'info>,
    
    #[account(
        init,
        payer = authority,
        space = InsurancePolicy::LEN,
        seeds = [b"insurance_policy", authority.key().as_ref(), policy_holder.key().as_ref()],
        bump
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct PurchasePolicy<'info> {
    #[account(mut)]
    pub policy_holder: Signer<'info>,
    
    #[account(
        mut,
        has_one = policy_holder,
        constraint = insurance_policy.status == PolicyStatus::Active
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
    
    #[account(mut)]
    pub policy_holder_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub insurance_pool_token_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct CheckTriggerConditions<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        has_one = authority,
        constraint = insurance_policy.status == PolicyStatus::Purchased
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
    
    /// CHECK: This is the oracle account that provides price data
    pub oracle_account: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct ExecutePayout<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        has_one = authority,
        constraint = insurance_policy.status == PolicyStatus::TriggeredPayout
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
    
    #[account(mut)]
    pub policy_holder_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub insurance_pool_token_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct CancelPolicy<'info> {
    #[account(mut)]
    pub policy_holder: Signer<'info>,
    
    #[account(
        mut,
        has_one = policy_holder,
        constraint = insurance_policy.status == PolicyStatus::Purchased
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
    
    #[account(mut)]
    pub policy_holder_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub insurance_pool_token_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct UpdateOracle<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        has_one = authority
    )]
    pub insurance_policy: Account<'info, InsurancePolicy>,
}

#[account]
pub struct InsurancePolicy {
    pub authority: Pubkey,
    pub policy_holder: Pubkey,
    pub oracle_address: Pubkey,
    pub trigger_threshold: i64,
    pub coverage_amount: u64,
    pub premium_amount: u64,
    pub expiry_timestamp: i64,
    pub created_timestamp: i64,
    pub purchased_timestamp: Option<i64>,
    pub triggered_timestamp: Option<i64>,
    pub payout_timestamp: Option<i64>,
    pub cancelled_timestamp: Option<i64>,
    pub trigger_price: Option<i64>,
    pub status: PolicyStatus,
    pub bump: u8,
}

impl InsurancePolicy {
    pub const LEN: usize = 8 + // discriminator
        32 + // authority
        32 + // policy_holder
        32 + // oracle_address
        8 + // trigger_threshold
        8 + // coverage_amount
        8 + // premium_amount
        8 + // expiry_timestamp
        8 + // created_timestamp
        9 + // purchased_timestamp (Option<i64>)
        9 + // triggered_timestamp (Option<i64>)
        9 + // payout_timestamp (Option<i64>)
        9 + // cancelled_timestamp (Option<i64>)
        9 + // trigger_price (Option<i64>)
        1 + // status
        1; // bump

    pub fn trigger_condition_type(&self) -> TriggerConditionType {
        // Simplified logic - in production, this would be configurable
        if self.trigger_threshold > 0 {
            TriggerConditionType::PriceAbove
        } else {
            TriggerConditionType::PriceBelow
        }
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum PolicyStatus {
    Active,
    Purchased,
    TriggeredPayout,
    PaidOut,
    Cancelled,
    Expired,
}

#[derive(Clone)]
pub enum TriggerConditionType {
    PriceAbove,
    PriceBelow,
    VolatilityAbove,
}

#[error_code]
pub enum InsuranceError {
    #[msg("Policy is not active")]
    PolicyNotActive,
    #[msg("Policy has expired")]
    PolicyExpired,
    #[msg("Policy has not been purchased")]
    PolicyNotPurchased,
    #[msg("Payout has not been triggered")]
    PayoutNotTriggered,
    #[msg("Policy cannot be cancelled")]
    PolicyCannotBeCancelled,
    #[msg("Invalid oracle data")]
    InvalidOracleData,
    #[msg("Insufficient funds")]
    InsufficientFunds,
}

#[cfg(test)]
mod tests {
    use super::*;
    use anchor_lang::prelude::*;
    use solana_program_test::*;
    use tokio;

    #[tokio::test]
    async fn test_initialize_policy() {
        // Test initialization of insurance policy
        // This would contain comprehensive tests for all contract functions
    }

    #[tokio::test]
    async fn test_purchase_policy() {
        // Test policy purchase flow
    }

    #[tokio::test]
    async fn test_trigger_conditions() {
        // Test trigger condition checking
    }

    #[tokio::test]
    async fn test_execute_payout() {
        // Test payout execution
    }

    #[tokio::test]
    async fn test_cancel_policy() {
        // Test policy cancellation
    }
}