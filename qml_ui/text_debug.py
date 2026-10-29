"""Opt-in typography diagnostics; contains no device data or file paths."""
import json, os

def report(app, window):
    from PySide6.QtCore import qVersion, QPointF
    from PySide6.QtGui import QFontInfo, QRawFont
    def emit(kind, data):
        print('TEXT_DEBUG '+kind+' '+json.dumps(data,ensure_ascii=False),flush=True)
    emit('environment',dict(qt=qVersion(),platform=app.platformName(),dpr=window.devicePixelRatio(),rounding=app.highDpiScaleFactorRoundingPolicy().name,graphics=window.rendererInterface().graphicsApi().name,environment={k:os.environ.get(k,'unset') for k in ('XDG_SESSION_TYPE','QT_SCALE_FACTOR','QT_SCALE_FACTOR_ROUNDING_POLICY','QSG_RHI_BACKEND','QT_QUICK_BACKEND','QSG_DISTANCEFIELD_ANTIALIASING')}))
    seen=set()
    positions=[]
    def visit(item):
        font=item.property('font')
        if font is not None and hasattr(font,'family'):
            actual=QFontInfo(font);raw=QRawFont.fromFont(font)
            try:
                render=item.property('renderType')
            except RuntimeError:
                # PySide may lack a converter for QQuickText::RenderType.
                meta=item.metaObject();idx=meta.indexOfProperty('renderType')
                render='QtRendering (declared)' if idx>=0 else 'not a text item'
            key=(font.family(),font.pixelSize(),font.weight(),str(render),font.hintingPreference())
            if key not in seen:
                seen.add(key)
                pos=item.mapToScene(QPointF(0,0))
                emit('style',dict(requested=font.family(),actual=actual.family(),style=actual.styleName(),pixels=font.pixelSize(),weight=int(font.weight()),hinting=font.hintingPreference().name,renderType=str(render),devicePosition=[pos.x()*window.devicePixelRatio(),pos.y()*window.devicePixelRatio()],tables={tag:len(raw.fontTable(tag)) for tag in ('fpgm','prep','cvt ','gasp')},cyrillic=all(raw.supportsCharacter(c) for c in list(range(0x410,0x450))+[0x401,0x451])))
            if str(render).startswith('QtRendering'):
                pos=item.mapToScene(QPointF(0,0));dpr=window.devicePixelRatio()
                positions.append((pos.x()*dpr,pos.y()*dpr))
        for child in item.childItems():visit(child)
    visit(window.contentItem())
    off=[pos for pos in positions if any(abs(v-round(v))>.01 for v in pos)]
    emit('alignment',dict(text_items=len(positions),off_device_pixel=len(off),examples=off[:8]))
