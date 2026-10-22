import { DojoIcon } from './DojoIcons.jsx';

export function DojoMark() {
  return <svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect x="2" y="2" width="44" height="44" rx="13" fill="#E8B878" /><path d="M9 13Q24 18 39 13M12 20H36M17 18V37M31 18V37M12 37H36" stroke="#183E37" strokeWidth="4" strokeLinecap="square" /><circle cx="24" cy="8" r="2" fill="#183E37" /></svg>;
}

// Stylized Master Splinter artwork drawn as editable SVG for the dojo theme.
export default function DojoMentor({ compact = false }) {
  return <svg className={compact ? 'dojo-mentor compact' : 'dojo-mentor'} viewBox="0 0 400 390" fill="none" role="img" aria-label="Master Splinter, your career coach, holding a practice scroll">
    <ellipse cx="204" cy="362" rx="129" ry="14" fill="#0C2725" opacity=".25" />
    <g stroke="#193D37" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M267 314C327 349 361 332 353 302C350 287 336 294 341 305" stroke="#B99B8A" strokeWidth="12" />
      <path d="M151 321L145 353H187L194 320M224 321L232 353H273L260 319" fill="#E2C898" />
      <path d="M145 345L136 357C136 365 177 366 188 358V345M233 345V358C246 365 283 364 281 356L271 345" fill="#243B35" />
      <path d="M150 205C121 220 111 253 105 278L133 292L158 254M257 208C283 212 295 237 310 255L286 278L253 252" fill="#976465" />
      <path d="M153 200L179 189H228L259 203L277 327C231 342 180 342 137 327Z" fill="#A97470" />
      <path d="M174 195L204 223L231 194L245 247L210 284L174 247Z" fill="#F8E9C9" />
      <path d="M171 198L150 222L172 236L163 248L199 306L204 223M236 197L257 220L237 237L248 249L211 306" fill="#80585C" />
      <path d="M144 282C182 291 235 291 272 280L273 300C230 310 181 310 142 302Z" fill="#21483F" />
      <path d="M204 288L223 297L213 309L198 301Z" fill="#E8B878" />
      <path d="M217 303L229 330L214 326L209 307M203 306L191 331L183 320L195 302" fill="#21483F" />
      <path d="M122 125C80 113 89 63 112 65C139 63 146 86 147 103M248 101C252 62 291 59 298 82C304 106 281 125 268 127" fill="#968878" />
      <path d="M115 104C101 88 107 74 115 76L134 96M260 99C269 74 284 72 283 86L274 107" fill="#E6B994" strokeWidth="3" />
      <path d="M119 111C126 70 166 58 203 61C253 58 286 90 285 137L280 171C267 208 233 224 202 222C161 225 123 204 113 171Z" fill="#A3947F" />
      <path d="M132 125C145 105 162 103 182 119L195 145L181 177L137 169ZM215 120C238 100 256 110 273 129L267 168L224 177L210 148Z" fill="#F5DFBC" stroke="none" />
      <path d="M123 150L153 175L183 173L203 188L224 174L254 177L280 151C276 198 250 221 205 227C161 223 130 203 123 150Z" fill="#F8E9CD" stroke="none" />
      <path d="M127 152L146 143L165 150M239 150L256 142L276 152" stroke="#82563F" strokeWidth="4" />
      <path d="M146 133Q159 124 174 133M232 133Q245 123 259 132" stroke="#F8E9CD" strokeWidth="8" />
      <rect x="135" y="137" width="53" height="34" rx="13" fill="#173E37" fillOpacity=".08" />
      <rect x="218" y="137" width="53" height="34" rx="13" fill="#173E37" fillOpacity=".08" />
      <path d="M188 149Q203 141 218 149M123 145L135 149M271 149L283 144" />
      <path d="M155 151Q161 146 168 151M236 151Q243 146 250 151" strokeWidth="3" />
      <path d="M192 174Q203 168 214 174L203 184Z" fill="#284139" />
      <path d="M203 184V191M190 192Q203 204 217 191" strokeWidth="3" />
      <path d="M184 201L190 223L198 218L205 235L214 217L222 219L225 199" fill="#E3D7BE" strokeWidth="2" />
      <path d="M185 181L149 175M184 189L142 193M221 181L256 173M222 190L263 193" stroke="#EEE2C9" strokeWidth="2" />
      <path d="M142 184L169 188M236 188L264 183" stroke="#B97B56" strokeWidth="2" />
      <path d="M107 267C101 254 89 256 89 268V284C90 300 119 303 127 290L128 280" fill="#C88155" />
      <g transform="rotate(-14 122 259)"><rect x="90" y="230" width="63" height="66" rx="4" fill="#F5DFB1" /><path d="M91 233H153M101 247H140M101 258H137M101 269H127" stroke="#9B7850" strokeWidth="3" /><path d="M86 229H156M88 298H158" stroke="#7C583F" strokeWidth="8" /></g>
      <path d="M292 254C300 245 314 251 316 263C317 276 302 284 291 276" fill="#C88155" />
      <path d="M313 215L309 349" stroke="#D9AE76" strokeWidth="9" />
      <path d="M314 210L308 199L312 184L319 191L318 206" fill="#83A581" />
      <path d="M180 68L191 58L202 66L214 55L225 68" fill="#E9B879" />
    </g>
    <g fill="#F3D99D"><path d="M65 163L69 174L80 178L69 182L65 193L61 182L50 178L61 174Z" /><path d="M330 112L333 120L342 123L333 126L330 135L327 126L318 123L327 120Z" /></g>
  </svg>;
}

export function TurtlePortrait({ name }) {
  const colors = { Leonardo: '#5E9DBD', Raphael: '#BF665F', Donatello: '#9482B4', Michelangelo: '#DC9B56' };
  const color = colors[name] || colors.Leonardo;
  return <svg className="dojo-turtle" viewBox="0 0 110 110" fill="none" role="img" aria-label={name}>
    <circle cx="55" cy="55" r="52" fill="#F8EEDB" />
    <path d="M19 102C21 81 34 74 55 74C77 74 91 84 93 102" fill="#5F7960" stroke="#28463B" strokeWidth="3" />
    <path d="M36 88Q55 79 74 88L77 108H32Z" fill="#DDC88F" stroke="#28463B" strokeWidth="2" />
    <path d="M27 56C24 27 40 16 56 16C77 16 88 31 84 57C83 76 71 86 55 85C38 85 27 73 27 56Z" fill="#87A76F" stroke="#28463B" strokeWidth="3" />
    <path d="M28 38C46 43 66 32 84 38L83 56C63 50 48 59 27 53Z" fill={color} stroke="#28463B" strokeWidth="2" />
    <path d="M81 43L101 38L95 51L86 52M84 49L102 57L91 63L82 54" fill={color} stroke="#28463B" strokeWidth="2" />
    <path d="M35 45L48 46L45 52L36 51ZM63 44L77 43L75 50L65 51Z" fill="#FFF7E8" />
    <path d="M42 46V50M69 44V49" stroke="#28463B" strokeWidth="3" />
    <path d="M48 59L57 61M42 69Q55 78 69 67" stroke="#28463B" strokeWidth="2.5" strokeLinecap="round" />
    <path d="M44 72L65 71" stroke="#F7EBCF" strokeWidth="3" />
    <path d="M31 100L76 88" stroke="#805D42" strokeWidth="7" />
  </svg>;
}

export function PizzaProgress({ slices = 0 }) {
  return <svg className="dojo-pizza" viewBox="0 0 140 140" role="img" aria-label={`${slices} of 8 pizza slices earned`}>
    <circle cx="70" cy="73" r="61" fill="#A9784430" />
    {Array.from({ length: 8 }, (_, i) => {
      const start = (i * 45 - 90) * Math.PI / 180;
      const end = ((i + 1) * 45 - 90) * Math.PI / 180;
      const earned = i < slices;
      const point = (angle, radius) => [70 + Math.cos(angle) * radius, 70 + Math.sin(angle) * radius];
      const a = point(start, 59), b = point(end, 59);
      const pepperoni = point((start + end) / 2, 35);
      return <g key={i}><path d={`M70 70L${a.join(' ')}A59 59 0 0 1 ${b.join(' ')}Z`} fill={earned ? '#F3C75C' : '#ECE4CE'} stroke="#B79B6E" strokeWidth="1.5" /><path d={`M${a.join(' ')}A59 59 0 0 1 ${b.join(' ')}`} fill="none" stroke={earned ? '#D59D56' : '#D7CCB1'} strokeWidth="9" /><circle cx={pepperoni[0]} cy={pepperoni[1]} r="6" fill={earned ? '#B85F46' : '#D6CDB7'} />{earned && <circle cx={point(start + .23, 46)[0]} cy={point(start + .23, 46)[1]} r="2.3" fill="#67815B" />}</g>;
    })}
    <circle cx="70" cy="70" r="4" fill="#D4AB67" />
  </svg>;
}

export function TrainingIcon({ name }) {
  return <DojoIcon name={name} />;
}
