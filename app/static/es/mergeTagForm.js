const mergeForm = document.querySelector('#merge-tags-form');

if (mergeForm) {
	let rows = 0;
	const
		addRowLink = mergeForm.querySelector('#add-merge-item'),
		rowHtmlStr = mergeForm.querySelector(
			'.merge-tags-form-item').outerHTML;
	addRowLink.addEventListener('click', () => {
		++rows;
		newRow = rowHtmlStr.replace(/0/g, rows)
		const
			items = mergeForm.querySelectorAll('.merge-tags-form-item'),
			lastItem = items[items.length - 1];
		lastItem.insertAdjacentHTML('afterend', newRow);
	})
}