require("dotenv").config({ path: "../.env" });
require("@nomicfoundation/hardhat-verify");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: false
      },
      metadata: {
        bytecodeHash: "none",
        useLiteralContent: true
      }
    }
  },
  networks: {
    monad: {
      url: "https://testnet-rpc.monad.xyz/",
      accounts: process.env.DEPLOY_PRIVATE_KEY ? [process.env.DEPLOY_PRIVATE_KEY] : []
    }
  },
  sourcify: {
    enabled: true,
    apiUrl: "https://sourcify-api-monad.blockvision.org/",
    browserUrl: "https://testnet.monadvision.com/"
  },
  etherscan: {
    enabled: false
  },
  paths: {
    sources: "./src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
