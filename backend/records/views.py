from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import DocumentType
# Giả định serializer và permission đã được Thịnh/Tuyền tạo chung
from .serializers import DocumentTypeSerializer 
from .permissions import HasViewHosoPermission 

class DocumentTypeListView(generics.ListAPIView):
    serializer_class = DocumentTypeSerializer
    # Cần quyền view_hoso theo contract
    permission_classes = [IsAuthenticated, HasViewHosoPermission] 

    def get_queryset(self):
        # Scope đúng Hồ sơ (không trả loại của hồ sơ khác)
        dossier_id = self.kwargs.get('dossier_id')
        
        # Dùng select_related('dossier') để tránh N+1 query
        queryset = DocumentType.objects.filter(dossier_id=dossier_id).select_related('dossier')
        
        # Search theo tên (không phân biệt hoa thường)
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
            
        # Lọc năm theo ngày lập
        year_filter = self.request.query_params.get('year', None)
        if year_filter and year_filter.isdigit():
            queryset = queryset.filter(created_at__year=int(year_filter))
            
        return queryset.order_by('sort_order', '-created_at')