
$(function(){
	$('.livepreview').livePreview({position:'top'});
	$('.minpreview').livePreview({scale:1,viewWidth:900,viewHeight:600});
	
	var $window = $(window),
		$header = $('header'),
		$button = $header.find('button'),
		$headerClone = $header.clone(),
		$headerCloneContainer = $('<div class=clone style=position:fixed;width:100%></div>'),
		$clonebutton = $headerCloneContainer.find('button'),
		headerOffsetTop = $header.offset().top,
		headerHeight = $header.outerHeight();
	
	$button.on('click',function(){
		if ($window.scrollTop() > headerOffsetTop){
			$headerCloneContainer
				.css({
					opacity:1,
					top:-$window.scrollTop()+headerOffsetTop
				})
				.animate({top:0},300);
			$header.addClass('open');
		};
	});
	$headerCloneContainer.append($headerClone);
	$headerCloneContainer.appendTo('body');
	$headerCloneContainer
		.css({'opacity':0})
		.find('button').on('click',function(){			
			var wintop = $window.scrollTop();

			$headerCloneContainer
				.animate({top:-wintop+headerOffsetTop},300)
				.animate({opacity:0,top:-headerHeight},0);
			$header.removeClass('open');
		});
	$window.on('scroll',function(){
		var wintop = $window.scrollTop();
		
		if ($header.hasClass('open')&&(wintop < headerOffsetTop)){
			$headerCloneContainer.css({opacity:0,top:-headerHeight});
			$header.removeClass('open');
			$window.trigger('scroll');
		};
		if (wintop > headerOffsetTop+headerHeight){
			$button.addClass('sticky');
		}else{
			$button.removeClass('sticky');
		};
	});
});