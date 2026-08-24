from rest_framework.views import APIView
from rest_framework.response import Response
from stocknlp.permissions import HasInterviewerKey

class VerifyKeyView(APIView):
    permission_classes = [HasInterviewerKey]

    def get(self, request):
        return Response(status=200)
