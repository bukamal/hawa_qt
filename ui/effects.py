# -*- coding: utf-8 -*-
"""Small visual effects helpers for PyQt widgets.

Effects are intentionally light; they should improve perceived polish without
slowing down tables or data-entry workflows.
"""
from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QParallelAnimationGroup
from PyQt5.QtWidgets import QGraphicsOpacityEffect


def fade_in(widget, duration: int = 160, start: float = 0.0, end: float = 1.0):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def cleanup():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass

    anim.finished.connect(cleanup)
    anim.start()
    widget._hawaa_fade_animation = anim
    return anim


def animate_width(widget, start_width: int, end_width: int, duration: int = 180, finished=None):
    group = QParallelAnimationGroup(widget)
    for prop in (b"minimumWidth", b"maximumWidth"):
        anim = QPropertyAnimation(widget, prop, widget)
        anim.setDuration(duration)
        anim.setStartValue(start_width)
        anim.setEndValue(end_width)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(anim)
    if finished:
        group.finished.connect(finished)
    group.start()
    widget._hawaa_width_animation = group
    return group
