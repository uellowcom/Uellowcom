/** @odoo-module **/
(function () {
    "use strict";
    var CM = {"أحمر":"#e63946","red":"#e63946","أزرق":"#457b9d","blue":"#457b9d","أخضر":"#2d6a4f","green":"#2d6a4f","أصفر":"#f5c518","yellow":"#f5c518","أسود":"#1a1a2e","black":"#1a1a2e","أبيض":"#f0f0f0","white":"#f0f0f0","بني":"#8b5e3c","brown":"#8b5e3c","رمادي":"#9ca3af","grey":"#9ca3af","gray":"#9ca3af","وردي":"#f9a8d4","pink":"#f9a8d4","بنفسجي":"#7c3aed","purple":"#7c3aed","برتقالي":"#f7941d","orange":"#f7941d"};
    function cfn(n) { var l=n.toLowerCase(); for(var k in CM){if(l.indexOf(k)!==-1)return CM[k];} return "#d1d5db"; }
    function injectSwatches() {
        document.querySelectorAll(".attribute_line,.o_variant_pills_attribute").forEach(function(line) {
            var lbl=line.querySelector("label,.attribute_name,strong");
            if(!lbl) return;
            var txt=lbl.textContent.trim().toLowerCase();
            if(txt.indexOf("color")===-1&&txt.indexOf("colour")===-1&&txt.indexOf("لون")===-1) return;
            if(line.querySelector(".ppc-color-swatches")) return;
            var vals=line.querySelectorAll(".variant_attribute_value,.o_variant_pill");
            if(!vals.length) return;
            var cont=document.createElement("div"); cont.className="ppc-color-swatches";
            vals.forEach(function(v) {
                var inp=v.querySelector("input[type='radio']");
                var nm=(v.querySelector(".attribute_value_name,label,span")||{}).textContent||"";
                if(!nm&&inp) nm=inp.getAttribute("data-attribute_value_name")||inp.value||"";
                nm=nm.trim();
                var img=inp?(inp.getAttribute("data-img")||inp.getAttribute("data-image")||""):"";
                var vid=inp?(inp.getAttribute("data-value-id")||""):"";
                if(!img&&vid) img="/web/image/product.attribute.value/"+vid+"/image/52x52";
                var bg=(inp?inp.getAttribute("data-color"):"")||cfn(nm);
                var sw=document.createElement("div");
                sw.className="ppc-color-swatch"+((inp&&inp.checked)?" active":"");
                var wrap=document.createElement("div"); wrap.className="ppc-swatch-img-wrap";
                if(img){var i=document.createElement("img");i.src=img;i.alt=nm;i.loading="lazy";i.onerror=function(){this.parentElement.style.background=bg;this.remove();};wrap.appendChild(i);}
                else wrap.style.background=bg;
                var label=document.createElement("span"); label.className="ppc-swatch-name"; label.textContent=nm;
                sw.appendChild(wrap); sw.appendChild(label);
                sw.addEventListener("click",function(){
                    if(inp){inp.click();inp.dispatchEvent(new Event("change",{bubbles:true}));}
                    cont.querySelectorAll(".ppc-color-swatch").forEach(function(s){s.classList.remove("active");});
                    sw.classList.add("active");
                });
                cont.appendChild(sw);
            });
            var orig=line.querySelector(".o_wsale_product_attrs,.css_attribute_color,.o_variant_pills");
            if(orig) orig.style.display="none";
            line.appendChild(cont);
        });
    }
    document.addEventListener("DOMContentLoaded",function(){
        injectSwatches();
        document.addEventListener("change",function(e){
            if(e.target&&e.target.name&&e.target.name.startsWith("ptal-")) setTimeout(injectSwatches,400);
        });
    });
})();
