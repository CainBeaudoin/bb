"""Template for a venue adapter. Copy to adapters/<name>.py.

Contract (see sites.py for working examples: Relay, DeBridge, Jumper, Across, Mayan):
  name      runner/site key, e.g. "layerswap" (also used in file names)
  bridg_id  the venue's data-venue id on Bridg's board, e.g. "layerswap"
  crop      (x, y, w, h) at a 1400x1000 viewport framing the swap widget + quote
  setup(page, route)  navigate and select USDC->USDC for route ("SOL","ETH") etc. Do NOT type the amount.
  enter(page)         type "100" into the amount field (use sites.type_into)
  read(page)          return None until a quote is visible, then a dict with at least
                      {"out": float USDC received}, plus anything useful
                      (fees charged on top, route/mode, eta, display decimals...).
If the venue cannot show a quote without a wallet / address / accepting terms, instead set
  ADAPTER = None
  BLOCKED = {"reason": "...", "url": "...", "checked": "<UTC ISO time>", "routes": [...]}.
A venue may support only some routes: give it  routes = [("SOL","ETH"), ...]  and the runner skips the rest.
"""
from sites import CHAINS, NUM, fnum, body_text, input_values, type_into  # noqa: F401
