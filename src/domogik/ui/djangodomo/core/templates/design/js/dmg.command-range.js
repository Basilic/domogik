const close_without_change = 10000; // 10 seconds
const close_with_change = 3000; // 3 seconds

(function($) {
    $.ui.widget_mini_core.subclass ('ui.widget_mini_command_range', {
        // default options
        options: {
            widgettype: 'command_range',
            nameposition: 'topleft'
        },

        _init: function() {
            var self = this, o = this.options;
            this.min_value = parseInt(o.min_value);
            this.max_value = parseInt(o.max_value);
            this.step = parseInt(o.step);
            this._rangeFront = $("<div class='front rangeleft' style='display:none'></div>");
            this._rangeLeft = $("<div style='display:none;' class='rotate rangeleft'><div class='bg rangeleft'></div></div>");
            this._rangeRight = $("<div style='display:none; -moz-transform: rotate(0deg);' class='rotate rangeright'><div class='bg rangeright'></div></div>");
            this.element.append(this._rangeFront)
                .append(this._rangeLeft)
                .append(this._rangeRight);
			this._button_plus = $("<div class='range_button range_plus' style='display:none'></div>");
			this._button_plus.click(function (e) {self.plus_range();e.stopPropagation()});
			this._button_minus = $("<div class='range_button range_minus' style='display:none'></div>");
			this._button_minus.click(function (e) {self.minus_range();e.stopPropagation()});
			this._button_max = $("<div class='range_button range_max' style='display:none'></div>");
			this._button_max.click(function (e) {self.max_range();e.stopPropagation()});
			this._button_min = $("<div class='range_button range_min' style='display:none'></div>");
			this._button_min.click(function (e) {self.min_range();e.stopPropagation()});
			this.element.addClass('closed');
			this.element.append(this._button_plus)
				.append(this._button_minus)
				.append(this._button_max)
				.append(this._button_min)
				.click(function (e) {self._onclick();e.stopPropagation();});
			this.element.keypress(function (e) {
					switch(e.keyCode) { 
					// User pressed "home" key
					case 36:
						self.max_range();
						break;
					// User pressed "end" key
					case 35:
						self.min_range();
						break;
					// User pressed "up" arrow
					case 38:
						self.plus_range();
						break;
					// User pressed "down" arrow
					case 40:
						self.minus_range();
						break;
					}
					e.stopPropagation();
				});
            this.setValue(null);
        },
        
        _onclick: function() {
            if (this.isOpen) {
                this.close();
				this._processValue();							
            } else {
                this.open();
            }
        },
        
        open: function() {
            var self = this, o = this.options;
            this._super();
            this._rangeFront.show();
            this._rangeLeft.show();
            this._setProcessingValue(this._processingValue);
			this._button_plus.show();
			this._button_minus.show();
			this._button_max.show();
			this._button_min.show();
			this.element.doTimeout( 'timeout', close_without_change, function(){
				self.close();
			});
		},
		
		close: function() {
            this._super();
            this._rangeFront.hide();
            this._rangeLeft.hide();
            this._rangeRight.hide();
			this._button_plus.hide();
			this._button_minus.hide();
			this._button_max.hide();
			this._button_min.hide();
		},
        
        setValue: function(value) {
            var self = this, o = this.options;
            if (value) {
                if (value >= this.min_value && value <= this.max_value) {
                    this.currentValue = value;
                } else if (value < this.min_value) {
                    this.currentValue = this.min_value;
                } else if (value > this.max_value) {
                    this.currentValue = this.max_value
                }
                this._processingValue = this.currentValue;
                var percent = (this.currentValue / (this.max_value - this.min_value)) * 100;
                this._displayIcon('range_' + findRangeIcon(o.usage, percent));
                this._displayValue(this.currentValue);
            } else { // unknown
                this._processingValue = 0;
                this._displayIcon('unknown');
                this._displayValue(null);
            }
        },
        
        _processValue: function() {
			if (this._processingValue != this.currentValue) {
                this.runAction({value: this._processingValue});
			}
		},

		plus_range: function() {
            var self = this, o = this.options;
			var value = ((this._processingValue + this.step) / this.step) * this.step;
      		this._resetAutoClose();
			this._setProcessingValue(value);
		},
		
		minus_range: function() {
            var self = this, o = this.options;
			var value = ((this._processingValue - this.step) / this.step) * this.step;
      		this._resetAutoClose();
			this._setProcessingValue(value);
		},
		
		max_range: function() {
            var self = this, o = this.options;
      		this._resetAutoClose();
			this._setProcessingValue(this.max_value);
		},
		
		min_range: function() {
            var self = this, o = this.options;
      		this._resetAutoClose();
			this._setProcessingValue(this.min_value);
		},
		
		_resetAutoClose: function() {
			var self = this;
			this.element.doTimeout( 'timeout', close_with_change, function(){
                self.close();
				self._processValue();
			});	
		},
        
        _displayValue: function(value) {
            var self = this, o = this.options;
            if (value) {
    			this._writeStatus(value + o.unit);                
            } else { // Unknown
    			this._writeStatus('---' + o.unit);                                
            }
        },
        
		_setProcessingValue: function(value) {
            var self = this, o = this.options;
			if (value >= this.min_value && value <= this.max_value) {
				this._processingValue = value;
			} else if (value < this.min_value) {
				this._processingValue = this.min_value;
			} else if (value > this.max_value) {
				this._processingValue = this.max_value
			}
			var percent = (this._processingValue / (this.max_value - this.min_value)) * 100;
            this._writeStatus(this._processingValue + o.unit);
            this._displayProcessingRange(percent);
		},

        _displayProcessingRange: function(percent) {
            var self = this, o = this.options;
            if (percent < 50) {
                var deg = (percent * 180) / 50;
                this._rangeLeft.css('-moz-transform', 'rotate(-' + deg + 'deg)');
                this._rangeRight.hide();
            } else {
                var deg = ((percent-50) * 180) / 50;
                this._rangeLeft.css('-moz-transform', 'rotate(-180deg)');
                this._rangeRight.css('-moz-transform', 'rotate(-' + deg + 'deg)');
                this._rangeRight.show();
            }
        },

        cancel: function() {
            this.setValue(this.currentValue);
            this._super();
        },
        
        /* Valid the processing state */
        valid: function(confirmed) {
            this._super();
            this.setValue(this._processingValue);
        }
    });
})(jQuery);