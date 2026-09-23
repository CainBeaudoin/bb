# Platforms and venues: how each was checked

This file records, for every site in the benchmark, how its quote is reached, what it showed and when. All times are UTC on 2026-09-23.

**Safety rules applied everywhere:**
- A fresh browser context was used for every site. Cain's own Chrome was never used, since it has a funded wallet connected to OpenSea.
- No wallet was ever connected. Nothing was signed, approved, swapped, deposited or confirmed.
- No address was typed into any site.
- No terms were accepted and no account was created by the agent.

**Account details are deliberately left out.** The repo is public, so no emails, wallet addresses, deposit addresses, QR codes or session data appear here. Session folders (`profiles/`) are git- and Vercel-ignored.

---

## Competitor platforms

### Signed-in re-check (built-in browser pane, about 13:55–14:07 UTC)

Cain signed in to each platform directly in the Claude desktop app's browser pane. The agent never typed or saw a password. The agent then only opened menus and read what they showed.

The pane was kept at a 1440×900 desktop viewport, because the mobile layout hides features.

#### Axiom (axiom.trade)

Result: **PARTIAL.** It has cross-chain features, but it can't price 100 USDC without funds in the account.

Path to the cross-chain Convert:
1. Click **Portfolio** in the top navigation.
2. Click the **Deposit** button at top right. This opens the "Exchange" dialog, which has three tabs: **Convert | Deposit | Buy**.
3. Choose **Convert**. The page describes it as "Swap SOL on Solana for BNB on BNB".
4. Set the destination first, via the **Gaining** token menu. Hover a chain to get its submenu, then pick **Ethereum → USDC**.
5. Then set the source, via the **Converting** token menu. Hover **Solana**, then pick **USDC**.

   Chains offered: Solana, Robinhood, Arc, BNB, Ink, HyperEVM, Base, Ethereum, Hyperliquid, Polymarket.

   Tokens per chain: SOL/ETH/BNB, USDC, USDT, USD1, USDG.

   The dialog then read *"Swap USDC on Solana for USDC on Ethereum"*, with an indicative rate of 1 USDC = 1.0000 USDC.

   Notes on this widget:
   - Pressing **Escape** resets the pair, so don't use it.
   - Pick the destination before the source. Picking a token that's already on the other side flips the pair.
6. Type `100` in Converting. **The field clamps to the wallet balance (0) and shows 0.000**, so no 100 USDC quote is produced.

Path to the auto-bridged deposit (Solana is the destination):
- Open **Deposit → Deposit tab**. Set "Deposit from" to ETH, BSC or BASE and "Receive on" to SOL, then choose **Accepting: USDC**.
- The dialog says *"Funds are auto-bridged to your SOL wallet. Minimum of $3 (ETH) / $2 (BSC, Base) required for triggered bridging."*
- The fees shown are for the minimum amount only. Hover the Fees ⓘ icon for the breakdown.

| Route | Est. arrival | Price impact | Fees | Breakdown |
|---|---|---|---|---|
| ETH→SOL (at the $3 minimum) | ~26 s | −0.388% (~$0.01) | ~$0.27 | instant liquidity <$0.01, routing <$0.01, gas $0.27 |
| BSC→SOL (at the $2 minimum) | ~26 s | −8.357% (~$0.17) | ~$0.21 | instant liquidity <$0.01, routing <$0.01, gas $0.21 |
| Base→SOL (at the $2 minimum) | ~26 s | −0.455% | ~$0.02 | — |

These fees are indicative only. The page says fees and impact vary with the amount sent, so they are not compared against Bridg.

Before the sign-in, a fresh automated browser got a Cloudflare 403 from axiom.trade. The site loaded normally in the browser pane.

#### GMGN (gmgn.ai)

Result: **BLOCKED.**

1. Open the wallet button at top right. It shows Balance, a chain toggle and eight actions: Deposit, Buy, Withdraw, Consolidate, Distribute, Transfer, **Convert** and GMGN Card.
2. **Convert** shows *"Complete 2FA binding to enable Convert … The first binding is expected to take effect at 3 hours, during which Convert will be disable[d]."*

   Binding 2FA is a security-setting change, so only the account owner should make it. It was not done.
3. **Deposit** says *"This address only supports SOL, USDT, USDC, USD1 deposits via the Solana network."* It is same-chain only.

Before the sign-in, a fresh automated browser got a Cloudflare "you have been blocked" page.

#### Pump.fun (pump.fun)

Result: **BLOCKED (Solana only on the web).**

1. Click the **$0.00** balance button at top right. This opens the "Your balance" panel.
2. Click **Deposit**. The dialog says *"Send any Solana asset to your wallet address"* and *"Only send assets on the Solana network"*.

   It lists a minimum deposit of 0.01 SOL, 1 confirmation, ~15 s arrival and a network fee under $0.01.

The MoonPay cross-chain deposit mentioned in news reports did not appear on the web app. The site banner says "Pump is better on mobile", so it may be mobile-only.

#### FOMO (fomo.family)

Result: **BLOCKED (no chain-to-chain quote).**

1. Click **Deposit more** under "cash" at top right. The "Deposit with" dialog offers **Crypto** ("Transfer USDC from a crypto wallet") or Credit/debit ("Coming soon").
2. Choose **Crypto**. The dialog says *"Send USDC to add to your cash balance"*, with a network picker offering Solana, Base, BNB Chain, Monad, Robinhood Chain, Arc and Ethereum.

Every network deposits into one USD cash balance. No fee or quote is shown at deposit, and moving funds out needs a balance.

#### OpenSea (opensea.io/swap): working, no sign-in needed

- URL: `https://opensea.io/swap?fromChain={solana|ethereum|base}&fromAddress=<USDC>&toChain=…&toAddress=<USDC>`
- Switch the amount field from USD to USDC with the ⇅ toggle before typing.
- Provider: Relay, or LI.FI on SOL→Base. OpenSea currently shows a "Now: 0% OpenSea Fee" badge. BNB Chain is not offered.

### Logged-out checks (automated fresh Playwright, about 13:32 UTC)

- **Axiom and GMGN:** HTTP 403 from Cloudflare bot verification.
- **FOMO:** landing page only.
- **Pump.fun:** the Terms / over-18 "Continue" modal was not accepted.

Screenshots were saved locally under `probe/`, which is ignored by git, so they are not in the repo.

---

## Bridge venues (fresh Playwright, no wallet; quotes in `data/raw_quotes.jsonl`)

| Venue | How the route is set | Routes |
|---|---|---|
| Bridg | `https://bridg.now/swap/`: asset pickers, clicking `button[data-testid=asset-selector-option][data-asset=USDC][data-chain=…]`; per-venue rows from `[data-testid=board-row]` | all 6 |
| Relay | `https://relay.link/bridge/{to}?fromChainId=…&fromCurrency=<USDC>&toCurrency=<USDC>` | all 6 |
| deBridge | `https://app.debridge.finance/?inputChain=…&outputChain=…&inputCurrency=…&outputCurrency=…&dlnMode=simple` (adds a fixed fee on top of the input) | all 6 |
| LI.FI (Jumper) | `https://jumper.exchange/?fromChain=…&toChain=…&fromToken=…&toToken=…` | all 6 |
| Across | `https://app.across.to/?from=…&to=…&inputToken=USDC&outputToken=USDC` | all 6 |
| Mayan | `https://swap.mayan.finance/`: token boxes, then chain, then search by USDC contract | all 6 |
| Allbridge Core | `https://core.allbridge.io/?fee=native&ft=USDC&tt=USDC&f=…&t=…` (routes via CCTP; relayer fee on top in SOL/ETH) | SOL↔ETH, SOL↔Base |
| CCTP | via Portal: `https://portalbridge.com/usdc-bridge?fromChain=…&fromToken=USDC&toChain=…&toToken=USDC` (Circle's own bridge has no Solana) | SOL↔ETH, SOL↔Base |
| Husher | `https://www.husher.io/`: scripted pickers ("USD Coin / USDC / <network>") | all 6 |
| Layerswap | `https://layerswap.io/app?from=<NET>&to=<NET>&fromAsset=USDC&toAsset=USDC` | all 6 |
| Meson | `https://meson.fi/swap`: chain pickers under From/To | all 6 |
| SimpleSwap | `https://simpleswap.io/?from=usdc-<net>&to=usdc-<net>` (floating rate, "Best rate" card) | all 6 |
| Skip Go | `https://go.skip.build/?src_chain=…&src_asset=…&dest_chain=…&dest_asset=…` | SOL↔ETH, SOL↔Base |
| Symbiosis | `https://app.symbiosis.finance/swap?chainIn=…&chainOut=…&tokenIn=…&tokenOut=…` | SOL→ETH, ETH→SOL, BSC→SOL, Base→SOL |
| Rhino.fi | BLOCKED: the retail app was shut down in August 2026 (redirects to `rhino.fi/b2c-app-deprecation`) | none |
| Eco | BLOCKED: `portal.eco.com` has no Solana or BNB Chain | none |
| NEAR Intents | BLOCKED: `app.near-intents.org` has moved to near.com/swap, which needs a login | none |

The code for each venue is in `sites.py` (Bridg, Relay, deBridge, LI.FI, Across, Mayan) or `adapters/<venue>.py`. Blocked venues and platforms keep their reason, URL and check time in their `BLOCKED` dict.

---

## Bridg API diagnostics (`data/api/`, 14:45:35 UTC)

These were indicative quotes (`indicative: true`, which can't be executed) from `POST https://api.bridg.now/v1/bridge/quote`. They used the example sender and recipient from Bridg's docs, plus a randomly generated Solana address. The API was used only to explain gaps, never as the benchmark.

| File | Recipient | Relay out | Relay "destination fill gas" |
|---|---|---|---|
| `eth_sol_docs_recipient_2.json` | docs example (already holds USDC) | 99.945676 (= relay.link) | 0.004322 |
| `eth_sol_fresh_recipient.json` | random new address (no USDC account) | 99.744756 | 0.205242 (+20.1 bps) |
| `eth_sol_no_recipient.json` | none | error `recipient_required` | — |

Fee lines from the same responses:
- **Meson:** a flat "Meson LP fee" of 0.50.
- **Husher:** a flat 0.20 exchange fee plus 0.30 delivery fee.
- **Allbridge:** a 0.10 CCTP service fee.
- **LI.FI:** a "LIFI Fixed Fee" of 0.25.
- **CCTP:** a "Circle Forwarding Service fee and destination gas" of 0.16 on ETH→SOL.
