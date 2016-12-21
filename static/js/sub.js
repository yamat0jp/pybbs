
$(function(){
	$('.livepreview').livePreview({position:'top'});
	$('.minpreview').livePreview({scale:1,viewWidth:900,viewHeight:600});
	
	var $window = $(window),
		$header = $('header'),
		$button = $header.find('button'),
		$headerClone = $header.contents().clone(),
		$headerCloneContainer = $('<div class=clone style=position:fixed></div>'),
		$clonebutton = $headerCloneContainer.find('button'),
		headerOffsetTop = $header.offset().top,
		headerHeight = $header.outerHeight();
	
	$button.on('click',function(){
		$headerCloneContainer
			.css({
				'opacity':1,
				'top':-$window.scrollTop()
			})
			.animate({top:0},300);
		$header.addClass('open');
	});
	$headerCloneContainer.append($headerClone);
	$headerCloneContainer.appendTo('body');
	$headerCloneContainer
		.css({'opacity':0})
		.on('animate',function(){
			$clonebutton.css({
				top:$headerCloneContainer.attr('top')+headerHeight
			});
		});
	$headerCloneContainer.find('button')	
		.on('click',function(){			
			var wintop = $window.scrollTop();
		
			if ($header.hasClass('open')){			
				if (wintop < headerOffsetTop+headerHeight){
					$headerCloneContainer
						.animate({top:-wintop+headerOffsetTop},300)
						.animate({opacity:0},0);
				}
			}else{				
				$headerCloneContainer
					.css({top:-wintop+headerOffsetTop})
					.animate({top:0},300);
			};
			$header.toggleClass('open');
		});
	$window.on('scroll',function(){
		var wintop = $window.scrollTop();
			
		if (wintop > headerOffsetTop+headerHeight){
			$headerCloneContainer.css({opacity:1});
			$clonebutton.css({top:0});
			if ($headerCloneContainer.hasClass('open') && (wintop < headerOffsetTop)){

			};
		}else{
			$clonebutton.css({'opacity':0});
		};
		$button.css({'top':-wintop+headerOffsetTop+headerHeight});
	});
});