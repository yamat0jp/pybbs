
$(function(){
	$('div').on('click',function(){
		var $title = $(this),
			span1 = 1500,
			span2 = 200;
		$title.css('font-size','2em');
		$({deg:5}).animate({deg:365},{
			duration:500,
			progress:function(){
				$title.css({
					'-webkit-transform':'rotate('+this.deg+'deg)',
					'-ms-transform':'rotate('+this.deg+'deg)',
					'ransform':'rotate('+this.deg+'deg)'
				});
			}
		});
		$({deg:5}).delay(span1).animate({deg:0},{
			duration:span2,
			progress:function(){
				$title.css({	
					'-webkit-transform':'rotate('+this.deg+'deg)',
					'-ms-transform':'rotate('+this.deg+'deg)',
					'transform':'rotate('+this.deg+'deg)'
				});
			}
		});
		$title.delay(span1+span2).animate({'font-size':'1em'},1);
	});
});
