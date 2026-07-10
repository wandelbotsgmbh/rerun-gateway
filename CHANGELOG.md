## [1.2.1](https://github.com/wandelbotsgmbh/rerun-gateway/compare/v1.2.0...v1.2.1) (2026-07-10)

## [1.0.2](https://github.com/wandelbotsgmbh/rerun-gateway/compare/v1.0.1...v1.0.2) (2026-07-10)

## [1.0.1](https://github.com/wandelbotsgmbh/rerun-gateway/compare/v1.0.0...v1.0.1) (2026-07-07)

## 1.0.0 (2026-06-18)

### Features

* add devcontainer configuration ([195e332](https://github.com/wandelbotsgmbh/rerun-gateway/commit/195e332ebb01adab05a0f943d987b0121be4b2fb))
* add python feature, uv, remoteUser root, and MCP config ([3f46b12](https://github.com/wandelbotsgmbh/rerun-gateway/commit/3f46b1281a78bfecd76b5be11c0f6d3af5be6d65))
* **ci:** add build and publish jobs for rerun-logger image ([6800c58](https://github.com/wandelbotsgmbh/rerun-gateway/commit/6800c5827f9b5e57985f39e164f050191875527b))
* configurable server memory limit via RERUN_MEMORY_LIMIT env ([0e4494a](https://github.com/wandelbotsgmbh/rerun-gateway/commit/0e4494a8b9e94bd93a380b5fe24a6871353de95a))
* **devcontainer:** add apt-packages feature for openssh-client ([eec7a73](https://github.com/wandelbotsgmbh/rerun-gateway/commit/eec7a73ee9cd9cb252483669d27a0cbe08e95283))
* **devcontainer:** add azure-cli feature ([3720b7b](https://github.com/wandelbotsgmbh/rerun-gateway/commit/3720b7b9eb4f9b41b2fa2c6b05f9052d81eaf0ce))
* **devcontainer:** install openssh-client and azure-cli in Dockerfile ([b9a5735](https://github.com/wandelbotsgmbh/rerun-gateway/commit/b9a573528aafe036df08f290aa81e479c115ffe5))
* native gRPC support via local proxy, deploy via API ([b0ff4ea](https://github.com/wandelbotsgmbh/rerun-gateway/commit/b0ff4ea12c163e3f09d46b21af6defb56349d64b))
* rerun viewer as App CRD with fetch interceptor MITM ([c8cfa85](https://github.com/wandelbotsgmbh/rerun-gateway/commit/c8cfa85d0a800cbef24c5605ebe6018c564ae8d3))
* update version references to 1.1.2, add catalog CI job, update icons ([252915a](https://github.com/wandelbotsgmbh/rerun-gateway/commit/252915a98c84c71b349f1cb12c9274cf95eefa6b))
* use Azure ACR proxy for base images, upgrade to Python 3.12, parameterize rerun-sdk version ([e895303](https://github.com/wandelbotsgmbh/rerun-gateway/commit/e895303ef2995a47a053016bd396e98fa767644b))
* use existing pull secret instead of inline ACR token ([e11385e](https://github.com/wandelbotsgmbh/rerun-gateway/commit/e11385e9a72eded90b2266fe596cdcf24e700930))

### Bug Fixes

* add Safari workaround for ReadableStream upload in gRPC-web ([a11c837](https://github.com/wandelbotsgmbh/rerun-gateway/commit/a11c83749c71fb546053647a73ee1410d46b8be8))
* CI publish credentials, OOM fix with 2000Mi pod memory, v2 API migration ([1679ad3](https://github.com/wandelbotsgmbh/rerun-gateway/commit/1679ad30908ee88cffff753f8c15cb395ea0e786))
* **ci:** publish images to Azure registry instead of GitLab registry ([aea5527](https://github.com/wandelbotsgmbh/rerun-gateway/commit/aea552769252a59b7d08c87c5064f6b9a0ab25e6))
* **ci:** publish images to Azure registry instead of GitLab registry ([0e07dd4](https://github.com/wandelbotsgmbh/rerun-gateway/commit/0e07dd4dd20b6a2e9e83675336c8ba9f6f13887f))
* **ci:** remove @semantic-release/git to fix protected branch push failure ([7c65740](https://github.com/wandelbotsgmbh/rerun-gateway/commit/7c65740c6228c1630ab7c68183e3cfc6709bb0d4))
* **ci:** use correct ACR credentials and image path for publish ([951cd7a](https://github.com/wandelbotsgmbh/rerun-gateway/commit/951cd7af59e8dd173752d3fb1286af766621b9f1))
* **devcontainer:** fix SSL cert verification for uv Python and k8s API ([6715746](https://github.com/wandelbotsgmbh/rerun-gateway/commit/67157465de87fa52bb7e1c19e3c283d37d0991df))
* disable absolute redirects to prevent port 8080 in URLs ([79fc2ae](https://github.com/wandelbotsgmbh/rerun-gateway/commit/79fc2ae3bd60497660e6a19b4ca54f286150547c))
* **nginx:** bump all timeouts to 24d for long-lived gRPC streams ([2661faf](https://github.com/wandelbotsgmbh/rerun-gateway/commit/2661faf1e07def6b3ac050ccbde4d926d3a76b54))
* reduce default RERUN_MEMORY_LIMIT from 1000MB to 500MB ([79a2559](https://github.com/wandelbotsgmbh/rerun-gateway/commit/79a2559743bc58adc1b58ac4cdb6360021fc7a23))
* reduce RERUN_MEMORY_LIMIT to 500MB to fit 1000Mi pod cap ([f2b0fcf](https://github.com/wandelbotsgmbh/rerun-gateway/commit/f2b0fcf57665ff19aaa9a003f8817524b7903166))
* resolve rerun URL parse error for proxy connection ([e604e4f](https://github.com/wandelbotsgmbh/rerun-gateway/commit/e604e4f57b489ceb59930d04000180fd76dd2808))
* resolve wasm_bindgen ReferenceError and app icon 404 ([8f2d774](https://github.com/wandelbotsgmbh/rerun-gateway/commit/8f2d7745661610bf0140bb66f15b00b564971952))
* set client_max_body_size 0 to allow >1MB gRPC WriteMessages ([feac2cc](https://github.com/wandelbotsgmbh/rerun-gateway/commit/feac2ccd89bc8839c0ef630d552524b280f19867))
* use namespace-agnostic service name and simplify fetch interceptor ([9c47479](https://github.com/wandelbotsgmbh/rerun-gateway/commit/9c47479518958a8cc90cd0d2e5ff7ceaef43501b))
* use square local app icons instead of external non-square logo ([a61c909](https://github.com/wandelbotsgmbh/rerun-gateway/commit/a61c909235578804582d416429a7f5d94eb3aad4))
