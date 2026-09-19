from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consultations.models import ConsultationCase

from .models import CoachingPlan
from .serializers import CoachingPlanCreateSerializer, CoachingPlanSerializer, CoachingPlanUpdateSerializer
from .services import create_plan, publish_plan, update_plan


def plan_queryset():
    return CoachingPlan.objects.select_related("case__client", "case__service").prefetch_related("sections", "recommendations")


class ClientPlanListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        plans = plan_queryset().filter(case__client=request.user, status=CoachingPlan.Status.PUBLISHED)
        return Response(CoachingPlanSerializer(plans, many=True).data)


class ClientPlanDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, public_id):
        plan = get_object_or_404(plan_queryset(), public_id=public_id, case__client=request.user, status=CoachingPlan.Status.PUBLISHED)
        return Response(CoachingPlanSerializer(plan).data)


class ClientCasePlanListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, case_id):
        plans = plan_queryset().filter(case__public_id=case_id, case__client=request.user, status=CoachingPlan.Status.PUBLISHED)
        return Response(CoachingPlanSerializer(plans, many=True).data)


class StaffCasePlanListCreateView(APIView):
    permission_classes = (IsAdminUser,)

    def get_case(self, request, case_id):
        return get_object_or_404(ConsultationCase.objects.select_related("service", "client"), public_id=case_id, service__expert=request.user)

    def get(self, request, case_id):
        case = self.get_case(request, case_id)
        return Response(CoachingPlanSerializer(plan_queryset().filter(case=case), many=True).data)

    def post(self, request, case_id):
        case = self.get_case(request, case_id)
        serializer = CoachingPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = create_plan(case=case, author=request.user, **serializer.validated_data)
        return Response(CoachingPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class StaffPlanDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def get_plan(self, request, public_id):
        return get_object_or_404(plan_queryset(), public_id=public_id, case__service__expert=request.user)

    def get(self, request, public_id):
        return Response(CoachingPlanSerializer(self.get_plan(request, public_id)).data)

    def patch(self, request, public_id):
        plan = self.get_plan(request, public_id)
        serializer = CoachingPlanUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = update_plan(plan=plan, **serializer.validated_data)
        return Response(CoachingPlanSerializer(plan_queryset().get(pk=plan.pk)).data)


class StaffPlanPublishView(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request, public_id):
        plan = get_object_or_404(CoachingPlan.objects.select_related("case__service"), public_id=public_id, case__service__expert=request.user)
        plan = publish_plan(plan=plan)
        return Response(CoachingPlanSerializer(plan_queryset().get(pk=plan.pk)).data)
