use crate::Client;

use anyhow::{Context, Result};
extern crate serde;
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Serialize, Deserialize)]
pub struct LoanScheme {
    pub id: String,
    pub mincolratio: i64,
    pub interestrate: f64,
    pub default: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoanSchemeId {
    pub id: String,
}

use std::collections::HashMap;
pub type ListCollateralToken = HashMap<String, CollateralToken>;

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CollateralToken {
    pub token: String,
    pub factor: f64,
    pub fixed_interval_price_id: String,
    pub activate_after_block: i64,
    pub token_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TokenIdSymbol {
    id: String,
    symbol: String,
}

#[derive(Debug, Serialize, Deserialize)]
// #[serde(rename_all = "camelCase")]
pub struct GetLoanInfoResult {
    pub currentpriceblock: i64,
    pub nextpriceblock: i64,
    pub defaults: LoanInfoDefaults,
    pub totals: LoanInfoTotals,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoanInfoDefaults {
    pub scheme: String,
    pub maxpricedeviationpct: f32,
    pub minoraclesperprice: u32,
    pub fixedintervalblocks: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoanInfoTotals {
    pub schemes: u32,
    pub collateraltokens: u32,
    pub collateralvalueinusd: f64,
    pub loantokens: u32,
    pub loanvalueinusd: f64,
    pub openvaults: u32,
    pub openauctions: u32,
}

impl Client {
    pub fn get_default_loan_scheme(&self) -> Result<LoanScheme> {
        self.call::<Vec<LoanScheme>>("listloanschemes", &[])?
            .into_iter()
            .find(|scheme| scheme.default == true)
            .context("Could not get default loan scheme")
    }

    pub fn get_loan_scheme(&self, scheme_id: &str) -> Result<LoanScheme> {
        self.call::<LoanScheme>("getloanscheme", &[scheme_id.into()])
    }

    pub fn set_default_loan_schemes(&self, scheme_id: &str) -> Result<LoanScheme> {
        self.call::<LoanScheme>("setdefaultloanscheme", &[scheme_id.into()])
    }

    pub fn get_loan_schemes(&self, scheme_id: &str) -> Result<LoanScheme> {
        self.call::<LoanScheme>("getloanscheme", &[scheme_id.into()])
    }

    pub fn list_loan_schemes(&self) -> Result<Vec<LoanScheme>> {
        self.call::<Vec<LoanScheme>>("listloanschemes", &[])
    }

    pub fn create_loan_scheme(
        &self,
        min_col_ratio: u32,
        interest_rate: &str,
        id: &str,
    ) -> Result<String> {
        self.call::<String>(
            "createloanscheme",
            &[min_col_ratio.into(), interest_rate.into(), id.into()],
        )
    }
    pub fn loan_payback(&self, vault_id: &str, address: &str, amount: &str) -> Result<String> {
        self.call::<String>(
            "loanpayback",
            &[json!({
                "vaultId": vault_id,
                "from": address,
                "amounts": amount
            })],
        )
    }

    pub fn take_loan(&self, vault_id: &str, amount: &str) -> Result<String> {
        self.call::<String>(
            "takeloan",
            &[json!({ "vaultId": vault_id, "amounts":amount })],
        )
    }

    pub fn set_collateral_tokens(&self, token: &str) -> Result<String> {
        let data = json!({
            "token": token,
            "factor": 1,
            "fixedIntervalPriceId": format!("{}/USD", token)
        });
        self.call::<String>("setcollateraltoken", &[data])
    }

    pub fn list_collateral_tokens(&self) -> Result<ListCollateralToken> {
        self.call::<ListCollateralToken>("listcollateraltokens", &[])
    }

    pub fn get_collateral_token(&self, token: &str) -> Result<CollateralToken> {
        self.call::<CollateralToken>("getcollateraltoken", &[token.into()])
    }

    pub fn set_loan_tokens(&self, tokens: &[&str]) -> Result<()> {
        for &token in tokens {
            println!("Creating loan token {}...", token);

            if let Ok(_) = self.get_token(token) {
                println!("Token {} already exists", token);
                continue;
            }

            let data = json!({
                "symbol": token,
                "name": format!("{} token", token),
                "fixedIntervalPriceId": format!("{}/USD", token),
                "mintable": true,
                "interest": 1
            });
            let tx = self.call::<String>("setloantoken", &[data])?;
            self.await_n_confirmations(&tx, 1)?;
            println!("Minting 1000 {}...", token);
            self.mint_tokens(1000, token)?;
        }
        Ok(())
    }

    pub fn get_loan_info(&self) -> Result<GetLoanInfoResult> {
        self.call::<GetLoanInfoResult>("getloaninfo", &[])
    }
}

#[cfg(test)]
mod test {
    use super::*;
    #[test]
    fn get_default_loan_scheme() -> Result<()> {
        let client = Client::from_env()?;
        let list_loan_schemes = client.list_loan_schemes()?;
        if list_loan_schemes.len() > 0 {
            let loan_scheme = client.get_default_loan_scheme()?;
            assert_eq!(loan_scheme.default, true);
        }
        Ok(())
    }

    #[test]
    fn get_loan_info() -> Result<()> {
        let client = Client::from_env()?;
        client.get_loan_info()?;
        Ok(())
    }
}
