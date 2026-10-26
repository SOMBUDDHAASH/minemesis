"""
Viewer V2 Tab Registration Package.
"""

from viewer.ui.tabs.base import BaseTab, TAB_REGISTRY, register_tab
from viewer.ui.tabs.home import HomeTab
from viewer.ui.tabs.chronicle import ChronicleTab
from viewer.ui.tabs.people import PeopleTab
from viewer.ui.tabs.places import PlacesTab
from viewer.ui.tabs.books import BooksTab
from viewer.ui.tabs.faith import FaithTab
from viewer.ui.tabs.threads import ThreadsTab
from viewer.ui.tabs.world import WorldTab
from viewer.ui.tabs.dynasty import DynastyTab
from viewer.ui.tabs.diplomacy import DiplomacyTab

__all__ = [
    "BaseTab",
    "TAB_REGISTRY",
    "register_tab",
    "HomeTab",
    "ChronicleTab",
    "PeopleTab",
    "PlacesTab",
    "BooksTab",
    "FaithTab",
    "ThreadsTab",
    "WorldTab",
    "DynastyTab",
    "DiplomacyTab",
]
