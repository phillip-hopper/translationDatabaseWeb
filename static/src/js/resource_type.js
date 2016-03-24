
(function($) {
    $().ready(function() {
        console.log("READY");
        $('select[data-class="resource-type"]').change(function() {

            // no sub-types for obs or tw
            var sub_type_select = $('select[data-class="resource-subtype"]');
            switch (this.value) {
                case 'obs':
                case 'tw':
                    sub_type_select.hide();
                    break;

                default:
                    sub_type_select.show();
            }

            getSubTypeOptions(this.value);
        })
    });

    function getSubTypeOptions(resource_type) {

        $.ajax({
            dataType: 'json',
            url: '{% url "publishing:ajax_resource_subtypes" %}',
            data: {q: resource_type}
        })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.log('Error getting resource subtypes: (' + textStatus + ')' + errorThrown);
            })
            .done(function(data) {
                console.log(data);
            });
    }
})(jQuery);
