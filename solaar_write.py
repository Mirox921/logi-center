"""Scoped CLI adapter: an explicit setting must not play a shutdown animation on exit."""
import sys
from logitech_receiver import rgb_power
# Only this short-lived process: leave the applied lighting intact on close.
# No modification of the installed Solaar package or its normal GUI lifecycle.
rgb_power.cleanup = lambda device: rgb_power.stop(device)
from solaar.gtk import main
sys.exit(main())
