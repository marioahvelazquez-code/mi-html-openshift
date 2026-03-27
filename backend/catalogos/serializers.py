from rest_framework import serializers

class AreaSerializer(serializers.Serializer):
    id_area = serializers.IntegerField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)


class TemaSerializer(serializers.Serializer):
    id_tema = serializers.IntegerField()
    id_area = serializers.IntegerField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)
    tabla_destino = serializers.CharField()
    modo_carga = serializers.CharField()


class DiccionarioCampoSerializer(serializers.Serializer):
    id_campo = serializers.IntegerField()
    columna_excel = serializers.CharField()
    columna_bd = serializers.CharField()
    tipo_dato = serializers.CharField()
    longitud = serializers.IntegerField(allow_null=True)
    obligatorio = serializers.BooleanField()
    orden = serializers.IntegerField()