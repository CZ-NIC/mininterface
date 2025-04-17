from typing import Any, TypeVar


RecommendedWidget = type('BoolWidget', (), {})
BoolWidget = type('BoolWidget', (RecommendedWidget,), {})
CallbackButtonWidget = type('CallableWidget', (RecommendedWidget,), {})
SubmitButtonWidget = type('SubmitButtonWidget', (RecommendedWidget,), {})
""" NOTE EXPERIMENTAL Special type: Submit button """
FacetButtonWidget = type('FacetButtonWidget', (RecommendedWidget,), {})
""" NOTE EXPERIMENTAL"""
