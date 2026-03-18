from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Post
from ..serializers import PostSerializer

class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view for predicted posts.
    """
    queryset = Post.objects.select_related(
        'related_ticker', 'post_prediction', 'related_content', 'post_metadata'
    ).all()
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['related_ticker__symbol', 'post_prediction__prediction']
    ordering_fields = ['time_stamp']
    ordering = ['-time_stamp']
