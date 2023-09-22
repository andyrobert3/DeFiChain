use ain_evm::bytes::Bytes;
use sha3::Digest;
use jsonrpsee::core::{Error, RpcResult};
use jsonrpsee::proc_macros::rpc;
use primitive_types::H256;

#[rpc(server, client, namespace = "web3")]
pub trait MetachainWeb3RPC {
    /// Returns the current network ID as a string.
    #[method(name = "clientVersion")]
    fn client_version(&self) -> RpcResult<String>;
    /// Returns the current network ID as a string.
    #[method(name = "sha3")]
    fn sha3(&self, input: Bytes) -> RpcResult<H256>;
}

#[derive(Default)]
pub struct MetachainWeb3RPCModule {}

impl MetachainWeb3RPCServer for MetachainWeb3RPCModule {
    fn client_version(&self) -> RpcResult<String> {
        let version: [u64; 3] = ain_cpp_imports::get_client_version().map_err(|e| {
            Error::Custom(format!("ain_cpp_imports::get_client_version error : {e:?}"))
        })?;
        let commit = option_env!("GIT_HASH").ok_or_else(|| {
            Error::Custom(format!("missing GIT_HASH env var"))
        })?;
        let os = std::env::consts::OS;

        let version_str = format!("{}.{}.{}", version[0], version[1], version[2]);

        Ok(format!("Metachain/v{}/{}-{}", version_str, os, commit))
    }

    fn sha3(&self, input: Bytes) -> RpcResult<H256> {
        let keccak_256: [u8; 32] = sha3::Keccak256::digest(&input.into_vec()).into();
        Ok(H256::from(keccak_256))
    }
}
