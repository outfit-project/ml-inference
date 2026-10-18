"""Fixed zero-shot vocabulary for clear photos containing one garment.

Cosine similarity selects labels; these scores are not calibrated confidence.
Color hex values represent the selected color word, not a measured fabric swatch.
"""
GARMENTS = {
    'top': ('t-shirt', 'shirt', 'blouse', 'sweater', 'hoodie', 'tank top', 'polo shirt'),
    'bottom': ('jeans', 'trousers', 'shorts', 'skirt', 'leggings'),
    'outerwear': ('coat', 'jacket', 'blazer', 'cardigan', 'vest'),
    'shoes': ('sneakers', 'boots', 'sandals', 'heels', 'loafers', 'dress shoes'),
    'accessory': ('bag', 'hat', 'scarf', 'belt', 'sunglasses', 'watch'),
}
STYLES = ('casual', 'formal', 'sport', 'streetwear')
COLORS = {
    'black':'#171717', 'white':'#f5f5f5', 'gray':'#808080', 'navy':'#000080',
    'blue':'#2563eb', 'green':'#228b22', 'red':'#dc2626', 'pink':'#ec4899',
    'purple':'#9333ea', 'yellow':'#eab308', 'orange':'#f97316', 'brown':'#795548',
    'beige':'#d6c5a5',
}


class VocabularyClassifier:
    def __init__(self, text_features):
        self._garments = [(category,label) for category,labels in GARMENTS.items() for label in labels]
        self._garment_features = text_features([f'a photo of a {label}' for _,label in self._garments])
        self._style_features = text_features([f'a photo of {style} style clothing' for style in STYLES])
        self._color_features = text_features([f'a photo of a {color} garment' for color in COLORS])

    @staticmethod
    def _best(features, embedding):
        scores = [sum(x*y for x,y in zip(row,embedding,strict=True)) for row in features]
        return max(range(len(scores)),key=scores.__getitem__)

    def classify(self, embedding):
        category,subcategory=self._garments[self._best(self._garment_features,embedding)]
        style=STYLES[self._best(self._style_features,embedding)]
        color_hex=list(COLORS.values())[self._best(self._color_features,embedding)]
        return dict(category=category,subcategory=subcategory,style=style,color_hex=color_hex)
