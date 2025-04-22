from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('planner/', views.trip_planner, name='trip_planner'),
    path('my-trips/', views.my_trips, name='my_trips'),
    path('weather/<int:id>/', views.view_weather, name='view_weather'),
    path('edit/<int:id>/', views.edit_trip, name='edit_trip'),
    path('delete/<int:id>/', views.delete_trip, name='delete_trip'),
    path('packing-list/<int:id>/', views.view_packing_list, name='view_packing_list'),
    path('packing-list/<int:trip_id>/generate/', views.generate_packing_list, name='generate_packing_list'),
    path('packing-list/<int:trip_id>/smart-generate/', views.generate_smart_packing_list, name='generate_smart_packing_list'),
    path('packing-list/<int:trip_id>/add/', views.add_packing_item, name='add_packing_item'),
    path('packing-list/<int:trip_id>/delete/<int:item_id>/', views.delete_packing_item, name='delete_packing_item'),
    path('packing-list/<int:trip_id>/toggle/<int:item_id>/', views.toggle_packed_status, name='toggle_packed_status'),
    path('packing-list/<int:trip_id>/update-quantity/<int:item_id>/', views.update_item_quantity, name='update_item_quantity'),
    path('packing-list/<int:trip_id>/stats/', views.packing_list_stats, name='packing_list_stats'),
    path('outfits/<int:id>/', views.view_outfit_recommendations, name='view_outfit_recommendations'),
    path('outfits/<int:trip_id>/customize/<int:recommendation_id>/', views.customize_outfit, name='customize_outfit'),
    path('outfits/<int:trip_id>/regenerate/<int:recommendation_id>/', views.regenerate_outfit, name='regenerate_outfit'),
    path('outfits/<int:trip_id>/add-item/<int:recommendation_id>/', views.add_outfit_item, name='add_outfit_item'),
    path('outfits/<int:trip_id>/remove-item/<int:recommendation_id>/<int:item_id>/', views.remove_outfit_item, name='remove_outfit_item'),
    path('outfits/<int:trip_id>/update-activities/<int:recommendation_id>/', views.update_activities, name='update_activities'),
    path('outfits/<int:trip_id>/sync-to-packing-list/<int:recommendation_id>/', views.sync_outfit_to_packing_list, name='sync_outfit_to_packing_list'),
    path('all-outfits/', views.all_outfits, name='all_outfits'),
    path('generate-all-outfits/', views.generate_all_outfits, name='generate_all_outfits'),
    path('outfit-detail/<int:recommendation_id>/', views.view_outfit_detail, name='view_outfit_detail'),
] 